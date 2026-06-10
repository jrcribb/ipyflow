# ipyflow extension UI / end-to-end tests

[Galata](https://github.com/jupyterlab/jupyterlab/tree/main/galata) + Playwright
tests that launch a real JupyterLab against the **ipyflow** kernel and exercise
the extension's UI behavior (comm establishment, dependency-aware cell
decoration, reactive re-execution).

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

Playwright launches its own JupyterLab via `jupyter_server_test_config.py` on a
dedicated port (**8899** by default, override with `IPYFLOW_UITEST_PORT`) so it
never collides with a JupyterLab you already have running on :8888. No manually
running server is required.

## CI

The `ui-tests` CI job is **opt-in** (it's slow and browser-based). It runs only
when the workflow is manually dispatched (Actions → CI → *Run workflow*) or on a
pull request carrying the `run-ui-tests` label. Ordinary pushes/PRs skip it.
