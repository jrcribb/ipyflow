# -*- coding: utf-8 -*-
"""Deprecated shim: ``%load_ext ipyflow.pyccolo``.

This existed only because pyccolo had no IPython host of its own, so the way to
run bare pyccolo tracers in a notebook was to load all of ipyflow and then throw
away its dataflow tracer. pyccolo ships that host now.
"""
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from IPython import InteractiveShell


def load_ipython_extension(shell: "InteractiveShell") -> None:
    warnings.warn(
        "`%load_ext ipyflow.pyccolo` is deprecated; use `%load_ext pyccolo`, "
        "then `%pyccolo register <tracer>` (or `pyc.register_ipython_tracer(...)`).",
        DeprecationWarning,
        stacklevel=2,
    )
    shell.run_line_magic("load_ext", "pyccolo")


def unload_ipython_extension(shell: "InteractiveShell") -> None:
    shell.run_line_magic("unload_ext", "pyccolo")
