# -*- coding: utf-8 -*-
.PHONY: clean black blackcheck eslint imports build deploy_only deploy check check_no_typing test tests deps devdeps dev typecheck version bump extlink kernel uitest uitest-record uitest-report e2e jupyterlite jupyterlite-serve jupyterlite-dev docs docs_doctest

# Prefer uv if available, otherwise fall back to pip. Override with `make <t> PIP=...`.
ifeq ($(shell command -v uv 2>/dev/null),)
PIP := python -m pip
else
PIP := uv pip
endif

clean:
	rm -rf __pycache__ core/__pycache__ build/ core/build/ core/dist/ dist/ ipyflow.egg-info/ core/ipyflow_core.egg-info core/ipyflow/resources/labextension

build: clean
	./scripts/build.sh

version:
	./scripts/build-version.py

bump:
	./scripts/bump.sh

deploy_only:
	./scripts/deploy-all.sh

deploy: version build deploy_only

black:
	isort ./core
	./scripts/blacken.sh

blackcheck:
	isort ./core --check-only
	./scripts/blacken.sh --check

lint:
	ruff check ./core

imports:
	pycln ./core
	isort ./core

typecheck:
	./scripts/typecheck.sh

# this is the one used for CI, since sometimes we want to skip typcheck
check_no_typing:
	./scripts/runtests.sh

coverage:
	rm -f .coverage
	rm -rf htmlcov
	./scripts/runtests.sh --coverage
	mv core/.coverage .
	coverage html
	coverage report

xmlcov: coverage
	coverage xml

eslint:
	./scripts/eslint.sh

docs:
	$(MAKE) -C docs html

docs_doctest:
	$(MAKE) -C docs doctest

check: eslint blackcheck lint typecheck check_no_typing

test: check
tests: check

deps:
	$(PIP) install -r requirements.txt

devdeps:
	$(PIP) install -e .
	$(PIP) install -e .[dev]
	# reinstall ipyflow-core editable last: installing the root pins it to the
	# released version on PyPI, which would otherwise clobber the local checkout
	$(PIP) install -e ./core[dev]

extlink:
	./scripts/extlink.sh

kernel:
	python -m ipyflow.install --sys-prefix

dev: devdeps build extlink kernel

# Galata/Playwright UI end-to-end tests (launches JupyterLab in a browser).
uitest:
	./scripts/runtests.sh ui

# Like `make uitest`, but record a video + trace for every test (pass or fail);
# view them afterwards with `make uitest-report`.
uitest-record:
	IPYFLOW_UITEST_RECORD=1 ./scripts/runtests.sh ui

# Open the HTML report from the last UI test run (served on localhost).
uitest-report:
	cd frontend/labextension/ui-tests && npm run test:report

# Headless kernel comm-protocol end-to-end test (starts a real ipyflow kernel).
e2e:
	cd core && IPYFLOW_KERNEL_E2E=1 python -m pytest test/test_kernel_comm_e2e.py -v

# Port for the local JupyterLite demo server; override with `make ... LITE_PORT=8999`.
LITE_PORT ?= 8000

# Build the JupyterLite demo site into ./dist (labextension + ipyflow-core wheel
# + offline runtime dep wheels). Needs PyPI reachable to download the dep wheels;
# once built, the site runs fully offline in the browser.
jupyterlite:
	bash jupyterlite/build.sh dist

# Serve the JupyterLite demo. Builds it first only if ./dist isn't a built site
# yet, so re-serving an existing build is instant (no rebuild, no PyPI needed).
# Use `make jupyterlite` to force a fresh build. Override the port with LITE_PORT.
jupyterlite-serve:
	@test -f dist/lab/index.html || $(MAKE) jupyterlite
	@echo "Serving JupyterLite demo at http://127.0.0.1:$(LITE_PORT)/lab/index.html?path=demo.ipynb (Ctrl-C to stop)"
	python -m http.server -d dist $(LITE_PORT)

# Force a fresh build, then serve.
jupyterlite-dev: jupyterlite jupyterlite-serve
