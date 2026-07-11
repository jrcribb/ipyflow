# Configuration file for the Sphinx documentation builder.
#
# Full option reference:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# ``ipyflow`` is pip-installed in the Read the Docs build (see .readthedocs.yml),
# so autodoc can ``import ipyflow`` directly. For a local ``make html`` from a
# source checkout, prepend ``core/`` (the real ``ipyflow-core`` package lives
# there; the top-level ``ipyflow`` is a thin metapackage) and the bundled
# ``_ext`` dir (which holds the doctest harness).
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_here, "_ext"))
sys.path.insert(0, os.path.join(_here, "..", "core"))

# -- Project information -----------------------------------------------------

project = "ipyflow"
copyright = "2021, Stephen Macke"
author = "Stephen Macke"

# The full version, including alpha/beta/rc tags, and the short X.Y version.
try:
    from ipyflow import __version__ as release
except Exception:
    release = ""
version = ".".join(release.split(".")[:2])


# -- General configuration ---------------------------------------------------

master_doc = "index"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
]

# Every worked example in the guides/getting-started pages is a runnable
# ``.. testcode::`` block executed by ``make -C docs doctest`` (wired into CI), so
# the docs cannot silently drift from the library. Because ipyflow's reactive API
# only works when notebook code runs through a live ipyflow shell, the harness in
# ``docs/_ext/ipyflow_doctest.py`` spins one up and injects ``run_cell`` and
# ``reset_flow`` into every snippet's namespace (see that module for details).
doctest_global_setup = (
    "from ipyflow_doctest import global_setup\n"
    "globals().update(global_setup())\n"
)

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# Patterns to ignore when looking for source files.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Link out to the CPython docs for cross-references (e.g. :class:`ast.AST`).
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

# Keep autodoc output in source order rather than alphabetized.
autodoc_member_order = "bysource"


# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_title = f"ipyflow {version}" if version else "ipyflow"

# Keep the full nav tree expanded and deep enough to reach the Diátaxis
# subsections. https://sphinx-rtd-theme.readthedocs.io/en/stable/configuring.html
html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 3,
}

# Custom static files (CSS overrides, etc.), copied after the builtin static
# files so a same-named file overrides the theme default.
html_static_path = ["_static"]
