# -*- coding: utf-8 -*-
import sys
from typing import TYPE_CHECKING

import ipyflow.api
from ipyflow import singletons
from ipyflow.api import *  # noqa: F403

try:
    from ipyflow.kernel.kernel import IPyflowKernel, UsesIPyflowKernel
except ImportError:
    # Under JupyterLite / Pyodide there is no ipykernel-based kernel to build
    # IPyflowKernel on top of; ipyflow attaches at the shell level instead (see
    # the ``sys.platform == "emscripten"`` branch in load_ipython_extension).
    IPyflowKernel = None  # type: ignore
    UsesIPyflowKernel = None  # type: ignore

from ipyflow.shell import load_ipython_extension as load_ipyflow_extension, unload_ipython_extension as unload_ipyflow_extension
from ipyflow.models import cell_above, cell_below, cell_at_offset, cells, last_run_cell, namespaces, scopes, statements, symbols, timestamps
from ipyflow.singletons import flow, kernel, shell, tracer
from ipyflow.tracing.uninstrument import uninstrument

from . import _version
__version__ = _version.get_versions()['version']

if TYPE_CHECKING:
    from IPython import InteractiveShell


def _jupyter_server_extension_paths():
    return [{"module": "ipyflow"}]


def _jupyter_server_extension_points():
    return [{"module": "ipyflow"}]


def load_jupyter_server_extension(nbapp):
    from ipyflow.kernel.kernel import patch_jupyter_taskrunner_run

    patch_jupyter_taskrunner_run()


# holds the kernel -> frontend "ipyflow-client" comm under Pyodide, where there
# is no IPyflowKernel to hang it off of.
_pyodide_client_comm = None


def _load_ipython_extension_pyodide(ipy: "InteractiveShell") -> None:
    """Activate ipyflow inside JupyterLite's Pyodide kernel.

    The shell-level injection has already happened in the caller. Here we do the
    parts that the ipykernel-based ``IPyflowKernel.instance()`` would normally
    handle: create the flow singleton, register the ``ipyflow`` comm target on
    the process-wide comm manager, and announce ourselves to the frontend over
    the ``ipyflow-client`` comm. The kernel-class swap and the asyncio/
    nest_asyncio patches do not apply here.
    """
    global _pyodide_client_comm

    # A freshly opened browser notebook has no persisted dependency DAG, so the
    # default dag-based schedule has nothing to seed waiting/ready cells from and
    # never highlights anything. The liveness-based schedule instead derives
    # staleness directly from each cell's code, which is what we want in the
    # browser. flow.initialize() (fired on comm-open) reads this off the shell
    # config, so set it before the frontend connects.
    try:
        ipy.config.ipyflow.exec_schedule = "liveness_based"
    except Exception:
        pass

    from ipyflow.flow import NotebookFlow

    flow_ = NotebookFlow.instance()
    flow_.register_comm_target()
    _patch_pyodide_kernel_cell_id()

    from ipykernel.comm import Comm

    if _pyodide_client_comm is None:
        _pyodide_client_comm = Comm(
            target_name="ipyflow-client", comm_id="ipyflow-client"
        )
    _pyodide_client_comm.send({"type": "establish", "success": True})


def _patch_pyodide_kernel_cell_id() -> None:
    """Thread the executing cell id into ipyflow under JupyterLite/Pyodide.

    ``PyodideKernel.run(code)`` drops the execute-request metadata, so ipyflow's
    usual ``init_metadata`` hook (which pulls ``cellId`` out of the request and
    calls ``set_active_cell``) never fires. The kernel does stash the full parent
    message on ``kernel._parent_header`` though, and its ``metadata`` carries
    ``cellId`` -- so wrap ``run`` to set the active cell from it before each
    execution. This is what makes per-cell reactive staleness work in the browser
    (otherwise executions fall back to placeholder ids and never link up).
    """
    try:
        from pyodide_kernel.kernel import PyodideKernel
    except Exception:
        return
    orig_run = PyodideKernel.run
    if getattr(orig_run, "_ipyflow_patched", False):
        return

    async def run(self, code):
        try:
            ph = self._parent_header
            to_py = getattr(ph, "to_py", None)
            if to_py is not None:
                ph = to_py()
            cell_id = (ph or {}).get("metadata", {}).get("cellId")
            if cell_id is not None:
                from ipyflow.singletons import flow

                flow().set_active_cell(cell_id)
        except Exception:
            pass
        return await orig_run(self, code)

    run._ipyflow_patched = True  # type: ignore[attr-defined]
    PyodideKernel.run = run  # type: ignore[method-assign]


def load_ipython_extension(ipy: "InteractiveShell", do_asyncio_patches: bool = False) -> None:
    load_ipyflow_extension(ipy)
    if sys.platform == "emscripten":
        _load_ipython_extension_pyodide(ipy)
        return
    kernel = getattr(ipy, "kernel", None)
    if kernel is None:
        return
    cur_kernel_cls = kernel.__class__  # type: ignore
    if issubclass(cur_kernel_cls, IPyflowKernel):
        cur_kernel_cls.replacement_class = None  # type: ignore
    else:
        class GeneratedIPyflowKernel(singletons.IPyflowKernel, cur_kernel_cls, metaclass=UsesIPyflowKernel):  # type: ignore
            pass
        GeneratedIPyflowKernel.inject(prev_kernel_class=cur_kernel_cls, do_asyncio_patches=do_asyncio_patches)  # type: ignore

    if IPyflowKernel.client_comm is None:  # type: ignore
        from ipykernel.comm import Comm

        comm = Comm(target_name="ipyflow-client")  # type: ignore
        comm.comm_id = "ipyflow-client"  # type: ignore
        IPyflowKernel.client_comm = comm  # type: ignore
    IPyflowKernel.client_comm.send({"type": "establish", "success": True})  # type: ignore


def unload_ipython_extension(ipy: "InteractiveShell") -> None:
    unload_ipyflow_extension(ipy)
    if sys.platform == "emscripten":
        if _pyodide_client_comm is not None:
            _pyodide_client_comm.send({"type": "unestablish", "success": True})
        return
    kernel = getattr(ipy, "kernel", None)
    if kernel is None:
        return
    cur_kernel_cls = kernel.__class__
    assert issubclass(cur_kernel_cls, IPyflowKernel)  # type: ignore
    assert cur_kernel_cls.prev_kernel_class is not None  # type: ignore
    cur_kernel_cls.replacement_class = cur_kernel_cls.prev_kernel_class  # type: ignore

    # TODO: reset state here so that %reload_ext behaves like unload then load?

    if IPyflowKernel.client_comm is not None:  # type: ignore
        IPyflowKernel.client_comm.send({"type": "unestablish", "success": True})  # type: ignore


__all__ = ipyflow.api.__all__ + [
    "__version__",
    "cell_above",
    "cell_below",
    "cell_at_offset",
    "cells",
    "flow",
    "kernel",
    "last_run_cell",
    "namespaces",
    "scopes",
    "shell",
    "statements",
    "symbols",
    "timestamps",
    "tracer",
    "uninstrument",
]


def main():
    import sys
    # Remove the CWD from sys.path while we load stuff.
    # This is added back by InteractiveShellApp.init_path()
    # TODO: probably need to make this separate from ipyflow package so that we can
    #  completely avoid imports until after removing cwd from sys.path
    if sys.path[0] == "":
        del sys.path[0]

    from IPython.terminal import ipapp as app

    from ipyflow.shell import IPyflowTerminalInteractiveShell

    app.launch_new_instance(interactive_shell_class=IPyflowTerminalInteractiveShell)
