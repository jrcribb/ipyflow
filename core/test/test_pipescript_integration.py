# -*- coding: utf-8 -*-
"""
Basic integration tests for loading the pipescript extension inside ipyflow.

These cover that ``%load_ext pipescript`` works under ``IPyflowInteractiveShell``
(including pipescript's extension initialization, which registers its builtin
dynamic macros) and that basic pipe syntax evaluates correctly. Advanced
pipescript features (e.g. ``$`` placeholders, which induce traced lambdas whose
synthetic line numbers ipyflow's dataflow tracer cannot map) are intentionally
out of scope.
"""

import sys
from test.utils import make_flow_fixture

import pytest

from ipyflow.singletons import shell

# pipescript is an optional test dependency and requires Python >= 3.9.
pytest.importorskip("pipescript")
pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 9), reason="pipescript requires Python >= 3.9"
)


def _load_pipescript():
    # Load pipescript, threading our ``run_cell`` so the extension's deferred
    # builtin-dynamic-macro loading runs the macro-definition cells through it
    # (rather than the default ``shell.run_cell``). Our ``run_cell`` keeps
    # store_history False and pins execution_count so it stays in sync with
    # ipyflow's cell counter the way a real frontend would -- otherwise the macros
    # fail to expand. The ``pass`` cell fires the deferred post_run_cell hook (and
    # warms up the just-registered tracers). Loaded once -- the extension's
    # tracers persist on the shell across the per-test flow/tracer reset.
    if "pipescript" not in shell().extension_manager.loaded:
        import pipescript

        pipescript.load_ipython_extension_ipyflow(shell(), run_cell=run_cell_)
        run_cell_("pass")
        shell().extension_manager.loaded.add("pipescript")
    yield


# Reset dependency graph and ensure pipescript is loaded before each test
_flow_fixture, run_cell_ = make_flow_fixture(extra_fixture=_load_pipescript)


def run_cell(cell, **kwargs):
    run_cell_(cell, **kwargs)


def result():
    return shell().user_ns["result"]


def test_load_ext_pipescript():
    registered = {tracer.__name__ for tracer in shell().registered_tracers}
    assert "PipelineTracer" in registered, "got %s" % registered


# ---------------------------------------------------------------------------
# Forward / backward piping (``|>`` and ``<|``)
# ---------------------------------------------------------------------------


def test_basic_pipe():
    run_cell("result = (3, 4, 1, 5, 6) |> sorted |> tuple")
    assert result() == (1, 3, 4, 5, 6)


def test_backward_pipe():
    # ``<|`` is the low-precedence backward variant of ``|>``.
    run_cell("result = reversed .> list <| [1, 2, 3]")
    assert result() == [3, 2, 1]


def test_backward_varargs_pipe():
    # ``f <|* x`` is the backward variant of ``x *|> f`` -- i.e. ``f(*x)``.
    run_cell("result = (lambda a, b: a + b) <|* (2, 3)")
    assert result() == 5


def test_backward_kwargs_pipe():
    # ``f <|** x`` is the backward variant of ``x **|> f`` -- i.e. ``f(**x)``.
    run_cell("result = (lambda a, b: a + b) <|** {'a': 2, 'b': 3}")
    assert result() == 5


# ---------------------------------------------------------------------------
# Function composition pipes (``.>``, ``*.>``, ``**.>``)
# ---------------------------------------------------------------------------


def test_function_pipe():
    run_cell("reverse = reversed .> list")
    run_cell("result = [1, 2, 3] |> reverse")
    assert result() == [3, 2, 1]


def test_function_pipe_chained():
    run_cell("pipeline = sorted .> reversed .> list")
    run_cell("result = [3, 1, 2] |> pipeline")
    assert result() == [3, 2, 1]


def test_star_function_pipe():
    # ``*.>`` unpacks the tuple returned by the first function before applying
    # the second.
    run_cell("split_sum = (lambda x: (x, x + 1)) *.> (lambda a, b: a + b)")
    run_cell("result = split_sum(10)")
    assert result() == 21


def test_kwstar_function_pipe():
    # ``**.>`` unpacks the dict returned by the first function as keyword args.
    run_cell("h = (lambda x: {'a': x, 'b': x + 1}) **.> (lambda a, b: a + b)")
    run_cell("result = h(10)")
    assert result() == 21


# ---------------------------------------------------------------------------
# Partial-application pipes (``$>``, ``*$>``, ``**$>``)
# ---------------------------------------------------------------------------


def test_partial_pipe():
    # ``x $> f`` is ``functools.partial(f, x)``.
    run_cell("g = 2 $> pow")
    run_cell("result = g(10)")
    assert result() == 1024


def test_partial_pipe_varargs():
    # ``x *$> f`` is ``functools.partial(f, *x)``.
    run_cell("g = (2, 10) *$> pow")
    run_cell("result = g()")
    assert result() == 1024


def test_partial_pipe_kwargs():
    # ``x **$> f`` is ``functools.partial(f, **x)``.
    run_cell("g = {'base': 2, 'exp': 10} **$> (lambda base, exp: base ** exp)")
    run_cell("result = g()")
    assert result() == 1024


# ---------------------------------------------------------------------------
# Argument-unpacking pipes (``**|>``)
# ---------------------------------------------------------------------------


def test_kwargs_pipe():
    # ``x **|> f`` is ``f(**x)`` when ``x`` is a dict.
    run_cell("result = {'base': 2, 'exp': 10} **|> (lambda base, exp: base ** exp)")
    assert result() == 1024


# ---------------------------------------------------------------------------
# Null-aware pipes (``?>``, ``*?>``, ``**?>``)
# ---------------------------------------------------------------------------


def test_optional_pipe_none_short_circuits():
    # ``None ?> f`` evaluates to ``None`` without ever calling ``f``.
    run_cell("result = None ?> sorted")
    assert result() is None


def test_optional_pipe_non_none():
    run_cell("result = [3, 1, 2] ?> sorted")
    assert result() == [1, 2, 3]


def test_varargs_optional_pipe_none():
    run_cell("result = None *?> (lambda a, b: a + b)")
    assert result() is None


def test_kwargs_optional_pipe_none():
    run_cell("result = None **?> (lambda a, b: a + b)")
    assert result() is None


# ---------------------------------------------------------------------------
# Optional / permissive attribute chaining and nullish coalescing
# ---------------------------------------------------------------------------


def test_optional_chaining_none():
    run_cell("a = None")
    run_cell("result = a?.b.c")
    assert result() is None


def test_optional_chaining_present():
    run_cell("result = 'hello'?.upper()")
    assert result() == "HELLO"


def test_permissive_attr_missing():
    # ``a.?b`` is ``getattr(a, "b", None)``.
    run_cell("obj = object()")
    run_cell("result = obj.?nonexistent")
    assert result() is None


def test_permissive_attr_present():
    run_cell("result = 'hello' .?upper")
    run_cell("result = result()")
    assert result() == "HELLO"


def test_nullish_coalescing_falsey_left():
    # ``??`` only falls through on ``None`` -- other falsey values pass through.
    run_cell("result = 0 ?? 42")
    assert result() == 0


def test_nullish_coalescing_none_left():
    run_cell("result = None ?? 42")
    assert result() == 42


def test_nullish_coalescing_is_lazy():
    run_cell("calls = []")
    run_cell("def rhs():\n    calls.append(1)\n    return 99")
    run_cell("result = 5 ?? rhs()")
    assert result() == 5
    assert shell().user_ns["calls"] == []


# ---------------------------------------------------------------------------
# Quick-lambda macro (``f[...]``)
# ---------------------------------------------------------------------------


def test_quick_lambda():
    run_cell("result = f[$ + $](2, 3)")
    assert result() == 5


def test_quick_lambda_named_placeholders():
    run_cell("result = f[$a*$b + $b*$c + $a*$c](2, 3, 4)")
    assert result() == 26
