import { expect, test } from '@jupyterlab/galata';

/**
 * Shared helpers for the ipyflow Galata / Playwright end-to-end tests.
 *
 * The extension exposes the active session's store on `window.ipyflow`
 * (state/registry.ts → setDebugStore), so the tests observe ipyflow's frontend
 * state (comm status, dependency graph, ready/waiting sets, settings) by reading
 * that handle via `page.evaluate`. JupyterLab itself is exposed on
 * `window.jupyterapp` (Galata), which we use to drive the kernel directly (e.g.
 * a restart) without going through a confirmation dialog.
 */

/** Poll until the ipyflow comm has established (window.ipyflow is the store). */
export async function waitForComm(page: any): Promise<void> {
  await expect
    .poll(
      () =>
        page.evaluate(
          () => (window as any).ipyflow?.isIpyflowCommConnected ?? false
        ),
      { timeout: 60_000, message: 'ipyflow comm never connected' }
    )
    .toBe(true);
}

/** Create a notebook on the ipyflow kernel, populate `cells`, await the comm. */
export async function openIpyflowNotebook(
  page: any,
  cells: string[]
): Promise<void> {
  await page.notebook.createNew(undefined, { kernel: 'ipyflow' });
  // Wait for the comm to establish on the fresh (empty) notebook BEFORE adding
  // cells. The establish handler flips the notebook into windowed-scrollbar
  // mode and re-renders; letting that happen concurrently with galata's cell
  // construction races and can hang addCell (the cell DOM shifts underneath it).
  await waitForComm(page);
  for (let i = 0; i < cells.length; i++) {
    if (i === 0) {
      await page.notebook.setCell(0, 'code', cells[0]);
    } else {
      await page.notebook.addCell('code', cells[i]);
    }
  }
}

/** The union of the store's ready + waiting cell-id sets. */
export const readyAndWaitingCells = (page: any): Promise<string[]> =>
  page.evaluate(() => {
    const s = (window as any).ipyflow;
    return s ? [...(s.readyCells ?? []), ...(s.waitingCells ?? [])] : [];
  });

/** The model id of the cell at `index`, as ipyflow keys its graph by it. */
export const cellModelId = (
  page: any,
  index: number
): Promise<string | undefined> =>
  page.evaluate(
    (i: number) => (window as any).ipyflow?.notebook?.widgets?.[i]?.model?.id,
    index
  );

/** The execution count of the cell at `index` (null if never executed). */
export const execCount = (page: any, index: number): Promise<number | null> =>
  page.evaluate(
    (i: number) =>
      (window as any).ipyflow?.notebook?.widgets?.[i]?.model?.executionCount ??
      null,
    index
  );

/**
 * The text of a cell's outputs, read from the output *model* (not the DOM, which
 * may be virtualized away in ipyflow's windowed-scrollbar mode). Concatenates
 * stream text and `text/plain` mime data. Useful across a kernel restart, where
 * execution counts reset and so cannot be compared, but a changed printed value
 * still proves a cell re-executed.
 */
export const cellOutputText = (page: any, index: number): Promise<string> =>
  page.evaluate((i: number) => {
    const outputs = (window as any).ipyflow?.notebook?.widgets?.[i]?.model
      ?.outputs;
    if (!outputs) {
      return '';
    }
    let text = '';
    for (let k = 0; k < outputs.length; k++) {
      const json = outputs.get(k)?.toJSON?.() ?? {};
      if (typeof json.text === 'string') {
        text += json.text;
      }
      const plain = json.data?.['text/plain'];
      if (typeof plain === 'string') {
        text += plain;
      }
    }
    return text;
  }, index);

/** The input source text of the cell at `index` (read from its shared model). */
export const cellSource = (page: any, index: number): Promise<string | null> =>
  page.evaluate(
    (i: number) =>
      (window as any).ipyflow?.notebook?.widgets?.[
        i
      ]?.model?.sharedModel?.getSource() ?? null,
    index
  );

/**
 * Set the input source of the cell at `index` directly on its shared model.
 *
 * Prefer this over Galata's `page.notebook.setCell`, which retypes the source
 * into the CodeMirror editor (select-all + type). After a kernel swap, ipyflow's
 * windowed notebook can leave the editor without a focused selection, so the
 * select-all is dropped and the new text is *inserted* rather than replacing the
 * old -- e.g. `setCell('x = 42')` over `x = 1` yields `x = 42x = 1`, a syntax
 * error that silently breaks the cell. Writing the model is immune to that and
 * still fires the content-changed notifications ipyflow listens for.
 */
export async function setCellSource(
  page: any,
  index: number,
  source: string
): Promise<void> {
  await page.evaluate(
    ({ i, src }: { i: number; src: string }) => {
      (window as any).ipyflow?.notebook?.widgets?.[
        i
      ]?.model?.sharedModel?.setSource(src);
    },
    { i: index, src: source }
  );
}

/** A Playwright Locator for the cell at `index` in the foreground notebook. */
export async function cellLocator(page: any, index: number) {
  const nb = await page.notebook.getNotebookInPanelLocator();
  return nb.locator('.jp-Cell').nth(index);
}

/**
 * Whether ipyflow's dependency graph records cell `parentIndex` as a parent of
 * cell `childIndex` (i.e. the edge parent → child is known to the frontend).
 */
export const cellChildrenIncludes = (
  page: any,
  parentIndex: number,
  childIndex: number
): Promise<boolean> =>
  page.evaluate(
    ({ p, c }: { p: number; c: number }) => {
      const s = (window as any).ipyflow;
      const pid = s?.notebook?.widgets?.[p]?.model?.id;
      const cid = s?.notebook?.widgets?.[c]?.model?.id;
      return (s?.cellChildren?.[pid] ?? []).includes(cid);
    },
    { p: parentIndex, c: childIndex }
  );

/** Poll until the parent → child edge is present in the dependency graph. */
export async function waitForEdge(
  page: any,
  parentIndex: number,
  childIndex: number
): Promise<void> {
  await expect
    .poll(() => cellChildrenIncludes(page, parentIndex, childIndex), {
      timeout: 30_000,
      message: `dependency edge cell${parentIndex} -> cell${childIndex} never formed`
    })
    .toBe(true);
}

/** The store's current ipyflow exec mode ('lazy' | 'reactive' | undefined). */
export const execMode = (page: any): Promise<string | undefined> =>
  page.evaluate(() => (window as any).ipyflow?.settings?.exec_mode);

/** Poll until the store reports the given exec mode. */
export async function waitForExecMode(
  page: any,
  mode: 'lazy' | 'reactive'
): Promise<void> {
  await expect
    .poll(() => execMode(page), {
      timeout: 30_000,
      message: `exec mode never became ${mode}`
    })
    .toBe(mode);
}

/**
 * Select the cell at `index` (entering command mode) and press a key chord,
 * exercising one of ipyflow's notebook keybindings. `selectCells` leaves the
 * notebook focused in command mode, which is what the ipyflow bindings target.
 */
export async function pressOnCell(
  page: any,
  index: number,
  keys: string
): Promise<void> {
  await page.notebook.selectCells(index);
  await page.keyboard.press(keys);
}

/**
 * Restart with a fresh kernel and wait for ipyflow to re-establish its comm.
 *
 * We swap in a brand-new kernel of the same type via
 * `ISessionContext.changeKernel` rather than an in-place `KernelConnection`
 * restart. The two are equivalent for what these tests care about -- a kernel
 * with no execution history attached to the same notebook (so its persisted
 * `ipyflow` metadata still applies) -- but a fresh kernel is what the extension
 * actually wires reconnection to: `changeKernel` fires `session.kernelChanged`,
 * whose handler (comm/connect.ts) re-registers the `ipyflow-client` comm target
 * and reconnects, rebuilding the store. An in-place restart keeps the same
 * kernel id, fires no `kernelChanged`, and the comm never re-establishes.
 *
 * We null out `window.ipyflow` first so `waitForComm` cannot observe the stale
 * pre-restart store and return early; the reconnect path re-points the handle at
 * the fresh store (registry.setDebugStore) once it establishes.
 */
export async function restartKernel(page: any): Promise<void> {
  await page.evaluate(async () => {
    const sessionContext = (window as any).jupyterapp?.shell?.currentWidget
      ?.sessionContext;
    (window as any).ipyflow = null;
    await sessionContext.changeKernel({ name: 'ipyflow' });
  });
  await waitForComm(page);
}

/** Put ipyflow into reactive mode by running a `%flow mode reactive` line. */
export async function enableReactiveMode(page: any): Promise<void> {
  await page.evaluate(async () => {
    const kernel = (window as any).ipyflow?.session?.session?.kernel;
    await kernel.requestExecute({ code: '%flow mode reactive' }).done;
  });
  await waitForExecMode(page, 'reactive');
}

/**
 * A snapshot of every cell in the foreground notebook: source, execution count,
 * and output text. Read from the models, so it reflects the real notebook state
 * regardless of windowed-scrollbar virtualization. Handy for diagnosing failures
 * (e.g. a corrupted cell source from a stale edit) -- see
 * {@link attachNotebookDumpOnFailure}.
 */
export const dumpNotebook = (
  page: any
): Promise<
  Array<{
    index: number;
    id: string;
    source: string;
    executionCount: number | null;
    output: string;
  }>
> =>
  page.evaluate(() => {
    const widgets = (window as any).ipyflow?.notebook?.widgets ?? [];
    return widgets.map((w: any, index: number) => {
      const model = w?.model;
      const outputs = model?.outputs;
      let output = '';
      for (let k = 0; k < (outputs?.length ?? 0); k++) {
        const json = outputs.get(k)?.toJSON?.() ?? {};
        if (typeof json.text === 'string') {
          output += json.text;
        }
        const plain = json.data?.['text/plain'];
        if (typeof plain === 'string') {
          output += plain;
        }
      }
      return {
        index,
        id: model?.id,
        source: model?.sharedModel?.getSource?.() ?? '',
        executionCount: model?.executionCount ?? null,
        output
      };
    });
  });

/**
 * Register an afterEach hook that, when a test fails, attaches a JSON dump of the
 * notebook's cells (source / execution count / output) to the Playwright report.
 * Call this once inside a `test.describe` so a failed run shows the actual cell
 * contents -- which is exactly what was needed to spot a corrupted `x = 42x = 1`
 * source. Pass the `test` object from '@jupyterlab/galata'.
 */
export function attachNotebookDumpOnFailure(t: typeof test): void {
  t.afterEach(async ({ page }, testInfo) => {
    if (testInfo.status === testInfo.expectedStatus) {
      return;
    }
    try {
      const dump = await dumpNotebook(page);
      await testInfo.attach('notebook-cells', {
        body: JSON.stringify(dump, null, 2),
        contentType: 'application/json'
      });
    } catch {
      // Best-effort diagnostics only; never let this mask the real failure.
    }
  });
}

/**
 * After each schedule, ipyflow persists its dependency graph via a 200ms-
 * debounced notebook save. Galata deletes each test's temp directory on
 * teardown, so a save that fires mid-teardown 500s ("File Save Error"). Let the
 * debounced save flush while the notebook still exists before the test ends.
 */
export async function settleAutosave(page: any): Promise<void> {
  await page.waitForTimeout(1000);
}
