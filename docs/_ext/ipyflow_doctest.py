# -*- coding: utf-8 -*-
"""
Build-time doctest harness for the ipyflow documentation.

ipyflow's public API (``lift``, ``deps``, ``%flow``, ``%%memoize``, ...) does
nothing under a plain ``import ipyflow``: it only comes alive when notebook code
is executed through a running IPython shell that has ipyflow's tracer installed.
The test suite solves this with ``make_flow_fixture`` / ``run_cell`` in
``core/test/utils.py``; this module is a near-verbatim port of that harness,
exposed to Sphinx's ``sphinx.ext.doctest`` builder via ``doctest_global_setup``.

Every ``.. testcode::`` block in the docs therefore runs against a *live* ipyflow
shell, and ``make -C docs doctest`` (wired into CI under ``-W``) fails if a worked
example drifts from the library.

The public entry point is :func:`global_setup`, which ``conf.py`` splices into the
doctest namespace so that ``run_cell`` and ``reset_flow`` are in scope for every
snippet.
"""
import os
import sys
import textwrap

from pyccolo.tracer import PYCCOLO_DEV_MODE_ENV_VAR


def squish_text(text: str) -> str:
    """Normalize the indentation of a (possibly triple-quoted) cell body.

    Mirrors ``squish_text`` in ``core/test/utils.py``; inlined here so the docs
    build has no dependency on the test package (which imports ``pytest``). This
    lets ``.. testcode::`` blocks pass indented multi-line cell bodies (function
    and class definitions) to ``run_cell`` without worrying about the extra
    leading whitespace introduced by the surrounding directive.
    """
    if textwrap.dedent(text) == text:
        return text
    prev_indentation = 0
    transformed_text_lines = []
    for line in text.strip("\n").splitlines():
        line_without_indentation = line.lstrip()
        indentation = len(line) - len(line_without_indentation)
        if indentation == 0:
            indentation = prev_indentation
        else:
            prev_indentation = indentation
        transformed_text_lines.append(
            textwrap.indent(line_without_indentation, " " * indentation)
        )
    return textwrap.dedent("\n".join(transformed_text_lines))


def _ensure_shell() -> None:
    """Instantiate the ipyflow shell singleton once per build process.

    Mirrors ``scripts/test_runner.py``: the shell must exist before
    ``NotebookFlow`` is created, since ``NotebookFlow.__init__`` reads
    ``shell().config`` and registers the ``%flow`` magic.
    """
    from ipyflow.shell import IPyflowInteractiveShell
    from ipyflow.singletons import IPyflowShell

    if not IPyflowShell.initialized():
        IPyflowInteractiveShell.instance()


def _make_run_cell():
    """Build a ``run_cell`` closure equivalent to the one in ``core/test/utils.py``."""
    from ipyflow.data_model.cell import cells
    from ipyflow.singletons import flow, shell

    def run_cell(code, cell_id=None, cell_pos=None, ignore_exceptions=False) -> int:
        next_exec_counter = cells().next_exec_counter()
        shell().execution_count = next_exec_counter
        if cell_id is None:
            cell_id = next_exec_counter
        flow().set_active_cell(cell_id)
        if cell_pos is None:
            cell_pos = cells()._position_by_cell_id.get(cell_id, None)
        if cell_pos is None:
            cell_pos = cell_id if isinstance(cell_id, int) else next_exec_counter
        cells()._position_by_cell_id[cell_id] = cell_pos
        kwargs = {}
        if "cell_id" in shell().run_cell.__code__.co_varnames:
            kwargs["cell_id"] = cell_id
        # ipyflow installs a persistent ``StdstreamProxy`` over ``sys.stdout`` /
        # ``sys.stderr`` (it is never uninstalled -- that is correct for a live
        # Jupyter session). Sphinx's doctest builder, however, swaps ``sys.stdout``
        # (but not ``sys.stderr``) around each snippet, which desynchronizes the two
        # proxies and, under IPython >= 9's per-cell ``_tee`` write patch, sends
        # ``StdstreamProxy.__setattr__`` into infinite recursion. Save and restore
        # both streams around the cell so no proxy leaks past ``run_cell`` to be
        # re-captured as its own underlying stream.
        saved_stdout, saved_stderr = sys.stdout, sys.stderr
        try:
            shell().run_cell(squish_text(code), **kwargs)
        finally:
            sys.stdout, sys.stderr = saved_stdout, saved_stderr
        try:
            if not ignore_exceptions and getattr(sys, "last_value", None) is not None:
                last_tb = getattr(sys, "last_traceback", None)
                if last_tb is not None and last_tb.tb_frame.f_back is None:
                    # raised from cell code (not the harness); surface it so that
                    # ``assert`` statements inside a cell fail the doctest.
                    raise sys.last_value
        finally:
            sys.last_value = None
            sys.last_traceback = None
        return cell_id

    return run_cell


# Settings that are applied to ``flow().mut_settings`` *after* the flow is
# instantiated (only ``flow_direction`` is accepted by ``NotebookFlow.instance``).
_MUTABLE_SETTINGS = (
    "exec_mode",
    "exec_schedule",
    "highlights",
    "reactivity_mode",
)


def reset_flow(*, flow_direction="any_order", setup_stmts=(), **kwargs):
    """Reset ipyflow to a clean state and return a fresh ``run_cell``.

    This is the per-document reset (the singletons are process-global, so each
    ``.rst`` file starts from an empty dataflow graph). Extra keyword arguments in
    ``_MUTABLE_SETTINGS`` (``exec_mode``, ``exec_schedule``, ``highlights``,
    ``reactivity_mode``) are coerced to their enums and applied to
    ``flow().mut_settings`` so a single page can demonstrate multiple
    configurations.
    """
    from ipyflow.config import (
        ExecutionMode,
        ExecutionSchedule,
        FlowDirection,
        Highlights,
        ReactivityMode,
    )
    from ipyflow.flow import NotebookFlow
    from ipyflow.singletons import flow
    from ipyflow.tracing.ipyflow_tracer import DataflowTracer

    _enum_by_setting = {
        "exec_mode": ExecutionMode,
        "exec_schedule": ExecutionSchedule,
        "highlights": Highlights,
        "reactivity_mode": ReactivityMode,
    }
    mutable = {k: kwargs.pop(k) for k in _MUTABLE_SETTINGS if k in kwargs}

    _ensure_shell()
    NotebookFlow.clear_instance()
    NotebookFlow.instance(
        test_context=True,
        flow_direction=FlowDirection(flow_direction),
        **kwargs,
    )
    DataflowTracer.clear_instance()
    DataflowTracer.reset_bookkeeping()
    DataflowTracer.instance()

    for setting, value in mutable.items():
        setattr(flow().mut_settings, setting, _enum_by_setting[setting](value))

    run_cell = _make_run_cell()
    for stmt in (
        # The reactive helpers (deps, users, lift, code, ...) plus the model
        # accessors are pre-imported into every snippet's namespace so examples
        # stay terse, mirroring how pyccolo's docs pre-import ``pyc``. These setup
        # cells run before ``reset_cell_counter`` below, so they do not perturb the
        # cell numbers that timestamp-based examples assert on.
        "from ipyflow.api import *",
        "from ipyflow import (cells, symbols, namespaces, scopes, statements, "
        "timestamps, cell_above, cell_below, cell_at_offset, last_run_cell)",
        "import pyccolo as pyc",
        *setup_stmts,
    ):
        run_cell(stmt)
    flow().reset_cell_counter()
    return run_cell


def global_setup():
    """Return the doctest-namespace globals for one document.

    ``conf.py`` wires this into ``doctest_global_setup`` so that ``run_cell`` and
    ``reset_flow`` are pre-bound in every ``.. testcode::`` block, with the
    ``ipyflow.api`` names already imported into the notebook namespace.
    """
    os.environ[PYCCOLO_DEV_MODE_ENV_VAR] = "1"
    run_cell = reset_flow()
    return {"run_cell": run_cell, "reset_flow": reset_flow}
