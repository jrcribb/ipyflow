#!/usr/bin/env bash
#
# Build the ipyflow JupyterLite demo site (the target of the "launch in
# JupyterLite" README badge) into ./dist.
#
# It builds everything from *this checkout* rather than PyPI so the demo always
# reflects the current source:
#   1. the JupyterLab/Notebook-7 federated extension (frontend/labextension),
#   2. the ipyflow-core wheel (runs in the browser via piplite),
#   3. the runtime dependency wheels, bundled offline for a fast, robust load.
#
# Usage:  bash jupyterlite/build.sh [OUTPUT_DIR]   # default: ./dist
# Prereqs: Python 3.11+, Node 18+ (npm), and network access to build.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DIST="${1:-$ROOT/dist}"
# `jupyter lite build` auto-discovers (copies + indexes into pypi/all.json) any
# wheel placed in <lite-dir>/pypi -- so dropping our wheels here is all that's
# needed for piplite to resolve them offline (the PipliteAddon.piplite_urls
# config route only loads from the CWD, not --lite-dir, so it silently no-ops
# when the build runs from the repo root).
WHEELS="$HERE/pypi"
ROOTDIST="$HERE/rootdist"

rm -rf "$WHEELS" "$ROOTDIST" "$DIST"
mkdir -p "$WHEELS"

# Make sure `pip` and the `build` frontend are importable in the active
# interpreter, whether it's a uv venv (which ships without pip), a plain venv,
# or a system Python. The rest of the script then stays on the standard
# `python -m pip` / `python -m build` so it behaves identically everywhere --
# in particular `pip download` (below) has no `uv pip` equivalent.
echo "==> Ensuring pip + build + jupyter are available"
# Bootstrap pip without hitting the network first (ensurepip ships Python's own
# pip); only fall back to uv if that's somehow unavailable.
python -m pip --version >/dev/null 2>&1 \
  || python -m ensurepip --upgrade >/dev/null 2>&1 \
  || { command -v uv >/dev/null 2>&1 && uv pip install pip; }
# the PEP 517 build frontend; install only if it isn't already present
python -c "import build" >/dev/null 2>&1 || python -m pip install --quiet build
python -c "import jupyter" >/dev/null 2>&1 || python -m pip install --quiet jupyter

echo "==> Building the ipyflow federated labextension"
pushd "$ROOT/frontend/labextension" >/dev/null
npm ci
npm run build   # emits to core/ipyflow/resources/labextension
popd >/dev/null

echo "==> Building wheels"
# ipyflow-core: the package that actually runs in the browser
python -m build --wheel "$ROOT/core" --outdir "$WHEELS"
# root ipyflow wheel: ships the federated extension as share/jupyter data files
python -m build --wheel "$ROOT" --outdir "$ROOTDIST"

echo "==> Installing the labextension into the build env (for jupyter lite build)"
# --no-deps: we only want the share/jupyter/labextensions data files, not the
# full jupyter/jupyterlab/notebook dependency tree.
python -m pip install --no-deps "$ROOTDIST"/ipyflow-*.whl

echo "==> Bundling pure-Python runtime deps offline (fast, robust load)"
python -m pip download --only-binary=:all: --python-version 3.12 \
  --implementation py --abi none --platform any \
  pyccolo pipescript comm black astunparse -d "$WHEELS"
# keep only universal (pure-Python) wheels
find "$WHEELS" -name '*.whl' ! -name '*-none-any.whl' -delete || true
echo "  bundled $(ls "$WHEELS"/*.whl | wc -l | tr -d ' ') wheels into $(basename "$WHEELS")/"

echo "==> Building the JupyterLite site"
python -m pip install jupyterlite-core jupyterlite-pyodide-kernel jupyter_server
jupyter lite build --contents "$HERE/content" --lite-dir "$HERE" --output-dir "$DIST"

echo "==> Done. Serve locally with:  python -m http.server -d '$DIST' 8000"
echo "    then open http://127.0.0.1:8000/lab/index.html?path=demo.ipynb"
