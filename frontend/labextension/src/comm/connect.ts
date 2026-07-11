import { ISessionContext } from '@jupyterlab/apputils';
import { IDocumentManager } from '@jupyterlab/docmanager';
import { INotebookTracker, Notebook } from '@jupyterlab/notebook';
import { JSONValue } from '@lumino/coreutils';

import {
  clearDebugStore,
  getStore,
  initStore,
  resetStore,
  setDebugStore,
} from '../state/registry';
import { updateUI } from '../ui/decorations';
import { clearCellState } from '../ui/dom';
import { IConnectionContext } from './context';
import { createMessageHandler } from './messageHandlers';
import { createNotebookEventHandlers } from './notebookEvents';

/**
 * Pre-install (but do NOT activate) ipyflow under JupyterLite/Pyodide, so the
 * user can `%load_ext ipyflow` without a manual `%pip install` first. This only
 * `pip install`s `ipyflow-core` (resolved offline from the bundled piplite
 * index) -- it does not run `load_ipython_extension`, so nothing activates until
 * the user opts in. On a regular Jupyter kernel the `sys.platform` gate makes it
 * a no-op.
 *
 * Awaited before the comm is set up so it lands as the first execute on the
 * fresh kernel; `import ipyflow` is then ready by the time the user runs
 * `%load_ext ipyflow` (even from a "Run All").
 */
async function ensureIpyflowInstalled(session: ISessionContext): Promise<void> {
  const kernel = session.session?.kernel;
  if (kernel == null) {
    return;
  }
  const code = [
    'import sys as _sys',
    "if _sys.platform == 'emscripten':",
    '    try:',
    '        import piplite as _piplite',
    // keep_going=True mirrors what the `%pip install` magic does. Note it does
    // NOT skip deps that are entirely unresolvable (a missing-metadata lookup
    // still raises) -- it only aggregates "no pure-Python wheel" errors. All of
    // ipyflow-core's deps must therefore resolve from an offline index: comm /
    // traitlets / pyccolo / black / nest_asyncio are bundled by jupyterlite/
    // build.sh, ipykernel is stubbed by jupyterlite-pyodide-kernel, and ipython
    // ships in Pyodide's lockfile. nest_asyncio in particular is easy to miss
    // because it is a hard dep but is NOT in the Pyodide lockfile.
    "        await _piplite.install('ipyflow-core', keep_going=True)",
    '    except Exception:',
    '        pass',
  ].join('\n');
  try {
    await kernel.requestExecute({
      code,
      silent: true,
      store_history: false,
      stop_on_error: false,
    }).done;
  } catch {
    // Expected if the kernel is restarted during the heavy first load; the
    // install re-runs on reconnect (kernelChanged handler in setupComm).
  }
}

/**
 * Create the `ipyflow` data comm. We let the kernel comm manager assign the
 * comm id instead of pinning it to a fixed `'ipyflow'`: on a JupyterLite/Pyodide
 * kernel reconnect (e.g. the kernel stalling during the one-time in-browser
 * install) the previous comm may not be disposed yet, and re-creating it under a
 * fixed id throws "Comm is already created", leaving the session with a dead
 * comm. The kernel side keys off the target name, not the id, so a fresh id each
 * time is safe and reconnect-resilient.
 */
function createIpyflowComm(session: ISessionContext) {
  return session.session.kernel.createComm('ipyflow');
}

/**
 * Establish the ipyflow comm for a notebook session: create the store, build
 * the connection context, wire the notebook event handlers and message
 * dispatcher, and open the comm. Returns a disconnect handler that tears the
 * connection down.
 */
export function connectToComm(
  session: ISessionContext,
  notebooks: INotebookTracker,
  notebook: Notebook,
  docManager: IDocumentManager,
  allowSelfEstablish = false,
): () => void {
  const store = initStore(session.session.id);
  store.activeCell = notebook.activeCell;
  store.comm = createIpyflowComm(session);
  store.notebook = notebook;
  store.session = session;

  const ipyflowMetadata =
    (notebook.model as any).getMetadata?.('ipyflow') ?? ({} as any);

  const ctx: IConnectionContext = {
    store,
    session,
    notebooks,
    notebook,
    docManager,
    disconnected: false,
    onEstablishPayload: null,
    ipyflowMetadata,
    safeSend: null as any, // assigned just below
  };

  const commDisconnectHandler = () => {
    if (!store.comm.isDisposed) {
      store.comm.dispose();
    }
    ctx.disconnected = true;
    store.isIpyflowCommConnected = false;
    resetStore(session.session.id);
  };

  const safeSend = (data: JSONValue): void => {
    if (ctx.disconnected) {
      return;
    } else if (store.comm.isDisposed) {
      ctx.onEstablishPayload = data;
      const oldComm = store.comm;
      store.comm = createIpyflowComm(session);
      store.comm.onMsg = oldComm.onMsg;
      store.comm.open({
        interface: 'jupyterlab',
        cell_metadata_by_id: store.gatherCellMetadataAndContent(),
        cell_parents: ctx.ipyflowMetadata?.cell_parents ?? {},
        cell_children: ctx.ipyflowMetadata?.cell_children ?? {},
      });
    } else {
      store.comm.send(data);
    }
  };
  ctx.safeSend = safeSend;
  store.safeSend = safeSend;

  const handlers = createNotebookEventHandlers(ctx);

  // Wire the listeners that must be live before `establish`.
  for (const cell of notebook.widgets) {
    cell.model.stateChanged.connect(handlers.onExecution);
  }
  notebook.model.cells.changed.connect(handlers.onCellsAdded);
  notebooks.selectionChanged.connect(handlers.onSelectionChanged);

  // Re-render decorations whenever the store signals a change.
  store.changed.connect(() => updateUI(store, notebooks));

  store.comm.onMsg = createMessageHandler(ctx, handlers);

  store.comm.open({
    interface: 'jupyterlab',
    cell_metadata_by_id: store.gatherCellMetadataAndContent(),
    cell_parents: ctx.ipyflowMetadata?.cell_parents ?? {},
    cell_children: ctx.ipyflowMetadata?.cell_children ?? {},
  });

  // Fallback for kernels that cannot deliver the kernel-side `establish` reply
  // sent from inside their comm_open handler (JupyterLite/Pyodide: the worker is
  // mid-RPC and blocks its event loop between requests, so the reply never
  // lands). comm_open runs synchronously kernel-side there, so by now the kernel
  // has already initialized the comm target; if we still haven't been
  // established shortly after opening, drive the establish handling ourselves.
  //
  // Only do this when the connect was triggered by the `ipyflow-client`
  // establish (i.e. `%load_ext ipyflow` actually ran and registered the comm
  // target) -- NOT for the speculative connect on session-ready. Otherwise a
  // kernel with ipyflow not loaded (e.g. before `%load_ext`) would falsely
  // appear ipyflow-connected. On a normal kernel the real `establish` arrives
  // first and this no-ops regardless.
  if (allowSelfEstablish) {
    setTimeout(() => {
      if (ctx.disconnected || store.isIpyflowCommConnected) {
        return;
      }
      store.comm.onMsg({
        content: { data: { type: 'establish', success: true } },
      } as any);
    }, 2000);
  }

  return commDisconnectHandler;
}

/**
 * Activate-time wiring: track the foreground notebook for the debug hook and
 * register the `ipyflow-client` comm target (plus kernel-restart handling) for
 * each notebook as it is added.
 */
export function setupComm(
  notebooks: INotebookTracker,
  docManager: IDocumentManager,
): void {
  notebooks.currentChanged.connect((_, nbPanel) => {
    const session = nbPanel.sessionContext;
    if (session?.session == null) {
      clearDebugStore();
      return;
    }
    const store = getStore(session.session.id);
    setDebugStore(store ?? null);
    if (store?.isIpyflowCommConnected ?? false) {
      store.requestComputeExecSchedule();
    }
  });

  notebooks.widgetAdded.connect((_sender, nbPanel) => {
    const session = nbPanel.sessionContext;
    let commDisconnectHandler = () => resetStore(session.session.id);

    const registerCommTarget = () => {
      session.session.kernel.registerCommTarget(
        'ipyflow-client',
        (comm, _open_msg) => {
          comm.onMsg = (msg) => {
            const payload: any = msg.content.data;
            if (!(payload.success ?? true)) {
              return;
            }
            if (payload.type === 'unestablish') {
              commDisconnectHandler();
            } else if (payload.type === 'establish') {
              commDisconnectHandler();
              // `%load_ext ipyflow` ran and registered the comm target, so allow
              // the self-establish fallback (the JupyterLite data-comm establish
              // is not delivered on its own).
              commDisconnectHandler = connectToComm(
                session,
                notebooks,
                nbPanel.content,
                docManager,
                true,
              );
            }
          };
          commDisconnectHandler();
          commDisconnectHandler = connectToComm(
            session,
            notebooks,
            nbPanel.content,
            docManager,
            true,
          );
        },
      );
    };

    session.ready.then(async () => {
      clearCellState(nbPanel.content);
      await ensureIpyflowInstalled(session);
      registerCommTarget();
      commDisconnectHandler();
      commDisconnectHandler = connectToComm(
        session,
        notebooks,
        nbPanel.content,
        docManager,
      );
      session.kernelChanged.connect((_, args) => {
        if (args.newValue == null) {
          return;
        }
        clearCellState(nbPanel.content);
        commDisconnectHandler();
        resetStore(session.session.id);
        commDisconnectHandler = () => resetStore(session.session.id);
        session.ready.then(async () => {
          await ensureIpyflowInstalled(session);
          registerCommTarget();
          commDisconnectHandler = connectToComm(
            session,
            notebooks,
            nbPanel.content,
            docManager,
          );
        });
      });
    });
  });
}
