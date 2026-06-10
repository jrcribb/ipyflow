# ipyflow extension UI / end-to-end tests

[Galata](https://github.com/jupyterlab/jupyterlab/tree/main/galata) + Playwright
tests that launch a real JupyterLab against the **ipyflow** kernel and exercise
the extension's UI behavior (comm establishment, dependency-aware cell
decoration, reactive re-execution).

## Test files

- `tests/helpers.ts` — shared plumbing (no tests). Reads ipyflow's per-session
  store off `window.ipyflow` and drives JupyterLab via `window.jupyterapp`:
  `waitForComm`, `openIpyflowNotebook`, `waitForEdge` / `cellChildrenIncludes`
  (dependency graph), `execCount` / `cellOutputText` / `cellSource`,
  `setCellSource`, `restartKernel`, `enableReactiveMode`, and
  `attachNotebookDumpOnFailure` (attaches a JSON dump of every cell's
  source/output/exec-count to the report when a test fails).
- `tests/ipyflow.spec.ts` — comm establishment, dependency-aware ready
  decoration, reactive re-execution.
- `tests/hotkeys.spec.ts` — the ipyflow keybindings: forward slice
  (`Accel+J` / `Accel+ArrowDown`), backward slice (`Accel+K` / `Accel+ArrowUp`),
  alt-mode execute (`Ctrl/Accel+Shift+Enter`), and run-ready-cells (`Space`).
  Each asserts the exact set of cells that (re)ran.
- `tests/restart.spec.ts` — behavior across a kernel restart: the dependency
  graph persists (via notebook metadata) and reactive re-execution still works
  immediately after, and after idling.

### Gotchas worth knowing

- **Edit cells via `setCellSource` (the model), not `page.notebook.setCell`.**
  Galata's `setCell` retypes into the CodeMirror editor; in ipyflow's
  windowed-scrollbar notebook the editor can lose its selection, so the new text
  is _appended_ instead of replacing (e.g. `x = 1` → `x = 42x = 1`, a silent
  syntax error). `setCellSource` writes the shared model directly. The specs also
  assert `cellSource(...)` after editing to catch any recurrence.
- **Reactive / closure runs happen outside Galata's run path** (ipyflow calls
  `CodeCell.execute` directly), so `page.notebook.runCell`'s `waitForRun` hangs
  on them. Trigger reactive runs with a raw `page.keyboard.press('Control+Enter')`
  and poll `execCount` / `cellOutputText` for the effect.
- **The dependency graph only populates after a _patched_ run** (`runCell`,
  Shift/Ctrl+Enter), not `page.notebook.run()`; `waitForEdge` waits for it.
- **`restartKernel` swaps in a fresh kernel via `changeKernel`** (firing
  `session.kernelChanged`, which the extension wires reconnection to). An
  in-place `KernelConnection.restart()` does not fire it and the comm never
  reconnects.

## Prerequisites

The built extension and the ipyflow kernel must be installed in the active
environment. From the repo root:

```bash
make dev          # builds the labextension, symlinks it, installs the kernel
```

Verify:

```bash
jupyter labextension list   # jupyterlab-ipyflow ... enabled OK
jupyter kernelspec list     # ipyflow
```

## Running

```bash
cd frontend/labextension/ui-tests
npm install
npm run install-browser            # first time only (downloads chromium)
npm test                           # or: make uitest (from repo root)
```

Useful variants (run from this directory):

```bash
npx playwright test --headed   # watch the browser drive JupyterLab
npm run test:debug             # Playwright inspector
npm run test:report            # open the last HTML report (./playwright-report)
```

Note: the HTML report and other artifacts are written under
`frontend/labextension/ui-tests/` (not the repo root), so run
`npm run test:report` / `npx playwright show-report` from this directory.

### Recording video + trace

By default video/trace are kept only for failing tests. To capture a video and a
Playwright trace for **every** test (handy for watching the run or debugging a
green build), use the dedicated target from the repo root and then open the
report:

```bash
make uitest-record    # = make uitest, but with video + trace on for all tests
make uitest-report    # view the videos/traces in the HTML report
```

(Equivalently: `IPYFLOW_UITEST_RECORD=1 npm test` from this directory.)

Playwright launches its own JupyterLab via `jupyter_server_test_config.py` on a
dedicated port (**8899** by default, override with `IPYFLOW_UITEST_PORT`) so it
never collides with a JupyterLab you already have running on :8888. No manually
running server is required.

## CI

The `ui-tests` CI job is **opt-in** (it's slow and browser-based). It runs only
when the workflow is manually dispatched (Actions → CI → *Run workflow*) or on a
pull request carrying the `run-ui-tests` label. Ordinary pushes/PRs skip it.
