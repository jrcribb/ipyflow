# -*- coding: utf-8 -*-
"""``%load_ext pyccolo`` and ``%load_ext ipyflow`` must compose, in either order.

pyccolo owns the cell tracing driver; ipyflow takes it over rather than installing
a second set of AST/input transformers on top. These run in fresh subprocesses:
both the IPython shell and pyccolo's tracers are process-wide singletons, and the
extension-load ordering is the whole point of the test.
"""
import os
import subprocess
import sys
import textwrap

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))

_PREAMBLE = """
import sys
sys.path.insert(0, {test_parent!r})

import pyccolo as pyc
from pyccolo.emit_event import _TRACER_STACK
from IPython.testing.globalipapp import get_ipython

from test.composition_tracer import CountingTracer
import test.composition_tracer as ct

ip = get_ipython()
TRACER = "test.composition_tracer.CountingTracer"

def run(code):
    # store_history=True keeps IPython's execution_count in step with ipyflow's
    # cell counter; otherwise the two disagree on the cell's filename and
    # pyccolo's file filter rejects it.
    result = ip.run_cell(code, store_history=True)
    if result.error_in_exec is not None:
        raise AssertionError("cell %r raised %r" % (code, result.error_in_exec))
    return result

def hits():
    return len(ct.hits)
"""


def _probe(*body_parts: str) -> None:
    # Dedent each part independently: they are written at different indent levels,
    # and dedenting the concatenation would leave one of them indented -- silently
    # absorbing its statements into the preamble's last ``def``.
    script = (
        _PREAMBLE.format(test_parent=os.path.dirname(_TEST_DIR))
        + "".join(textwrap.dedent(part) for part in body_parts)
        + '\nprint("OK")\n'
    )
    proc = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True
    )
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    assert proc.stdout.strip().endswith("OK"), proc.stdout


_ASSERT_COMPOSED = """
assert pyc.ipython_driver(ip)._hosted, "ipyflow should own the driver"
# pyccolo must not have installed a second AST transformer on top of ipyflow's
assert ip.ast_transformers == [], ip.ast_transformers

names = [c.__name__ for c in pyc.registered_ipython_tracers(shell=ip)]
assert names[0] == "CountingTracer", names
assert set(names[1:]) == {"OutputRecorder", "DataflowTracer", "InterruptTracer"}, names

before = hits()
run("q1 = 1\\nq2 = 2\\nq3 = 3")
# exactly three before_stmt events, not six: the cell is instrumented once
assert hits() - before == 3, hits() - before
assert ip.user_ns["q3"] == 3

stack = [type(t).__name__ for t in _TRACER_STACK]
assert stack[0] == "CountingTracer", stack
"""


def test_pyccolo_then_ipyflow():
    _probe(
        """
        run("%load_ext pyccolo")
        run("%pyccolo register " + TRACER)
        before = hits()
        run("a = 1\\nb = 2")
        assert hits() - before == 2, "native driver should instrument"

        run("%load_ext ipyflow")
        """,
        _ASSERT_COMPOSED,
    )


def test_ipyflow_then_pyccolo():
    _probe(
        """
        run("%load_ext ipyflow")
        run("%load_ext pyccolo")
        run("%pyccolo register " + TRACER)
        """,
        _ASSERT_COMPOSED,
    )


def test_flow_register_tracer_shares_pyccolos_registry():
    _probe(
        """
        run("%load_ext ipyflow")
        run("%load_ext pyccolo")

        run("%flow register " + TRACER)
        assert "CountingTracer" in [
            c.__name__ for c in pyc.registered_ipython_tracers(shell=ip)
        ]

        run("%flow deregister " + TRACER)
        assert "CountingTracer" not in [
            c.__name__ for c in pyc.registered_ipython_tracers(shell=ip)
        ]

        # ...and the pyccolo-native spelling lands in ipyflow's view of the world
        run("%pyccolo register " + TRACER)
        assert "CountingTracer" in [t.__name__ for t in ip.registered_tracers]
        """
    )


def test_unload_ipyflow_hands_driver_back_to_pyccolo():
    _probe(
        """
        run("%load_ext ipyflow")
        run("%load_ext pyccolo")
        run("%pyccolo register " + TRACER)
        run("warmup = 1")

        run("%unload_ext ipyflow")
        # ipyflow's class swap is undone at the end of the *next* cell
        run("pass")
        assert type(ip).__name__ != "GeneratedIPyflowShell", type(ip).__name__
        assert not pyc.ipython_driver(ip)._hosted

        before = hits()
        run("r1 = 1\\nr2 = 2")
        assert hits() - before == 2, "native driver should have taken back over"
        assert ip.user_ns["r2"] == 2
        # and an instrumented cell still yields its Out[N]
        assert run("40 + 2").result == 42
        """
    )
