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

from ipyflow.data_model.cell import Cell
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


# ---------------------------------------------------------------------------
# Subscript-based macros (``map[...]``) in loops, comprehensions, and nested
#
# pipescript's ``map[...]`` macro relies on its MacroTracer intercepting
# ``before_subscript_load`` to swap the builtin ``map`` for an identity-subscript
# shim -- this is required for *correctness*, not mere observation. ipyflow's
# performance optimizations (pyccolo loop/comprehension guards, the external-
# call-depth limit, and repeated-call tracing-disable) each previously suppressed
# that swap on repeat executions, so the macro reached the real builtin and
# raised ``TypeError: type 'map' is not subscriptable``.
#
# Fixes (all keyed on a co-tracer that, like all of pipescript's, sets
# ``global_guards_enabled = False`` -- i.e. performs substitution, not mere
# observation):
#   * pyccolo treats such a tracer's handlers as guard-exempt (loops), and emits
#     a guard-exempt fallback for comprehension elements;
#   * ipyflow keeps tracing into the tracer's sandbox-generated lambdas instead
#     of disabling on call depth / repeated calls;
#   * ipyflow's get_position skips ``__hide_pyccolo_frame__`` infrastructure
#     frames so pipescript's pipe-application lambdas don't misattribute their
#     source line numbers to the executing cell.
# ---------------------------------------------------------------------------


def test_map_macro_in_for_loop():
    run_cell(
        "out = []\n"
        'for row in [["1", "2", "3"], ["4", "5", "6"]]:\n'
        "    out.append(row |> map[int] |> sum)\n"
        "result = out"
    )
    assert result() == [6, 15]


def test_map_macro_in_comprehension():
    run_cell("result = [row |> map[int] |> sum for row in [['1', '2'], ['3', '4']]]")
    assert result() == [3, 7]


def test_nested_map_macro():
    run_cell("result = [['1', '2'], ['3', '4']] |> map[map[int]] |> list")
    assert result() == [[1, 2], [3, 4]]


def test_nested_map_macro_across_loop_iterations():
    # Advent of Code 2015 day 2: 2x3x4 -> 34, 3x4x5 -> 74, sum -> 108.
    run_cell(
        'result = "2x3x4\\n3x4x5".strip().splitlines() '
        '|> map[$.split("x") |> map[int] '
        "*|> $l*$w*$h + 2*min($l+$w, $w+$h, $h+$l)] |> sum"
    )
    assert result() == 108


# ---------------------------------------------------------------------------
# Brace blocks (`macro{ ... }`)
#
# pipescript's BraceBlockTracer lets any macro written `macro[...]` also be
# written `macro{...}`, including multi-line *statement* bodies whose trailing
# expression is the result. Under ipyflow these previously failed outright: the
# block was stashed and the slice replaced with a marker, but (a) the marker was
# an undefined name that ipyflow's `before_subscript_slice` evaluated before the
# macro could substitute it (NameError), and (b) ipyflow invokes the syntax
# augmenter several times per cell, so a per-pass marker id made the augmenter
# non-idempotent and the cell ran uninstrumented. The compiled block is also
# synthetic sandbox code, so it must stay invisible to ipyflow's dataflow tracer
# (hidden compile frames + instrumenting the block with only the substituting
# tracers).
# ---------------------------------------------------------------------------


def test_brace_expression_block():
    run_cell("result = [0, 1, 2] |> map{ $ + 10 } |> list")
    assert result() == [10, 11, 12], result()


def test_brace_statement_block():
    run_cell(
        "result = [1, 2, 3, 4] |> map{\n"
        "    acc = 0\n"
        "    for i in range($):\n"
        "        acc += i\n"
        "    acc\n"
        "} |> list"
    )
    assert result() == [0, 1, 3, 6], result()


def test_brace_block_with_bare_pipeline_stage():
    # a bare pipe stage inside a block: the stage's `$` is the pipe argument
    # (left for PipelineTracer), not the block's collapse-`$`. Without the fix
    # both `$` collapse to the block input, giving `n |> (n+10)` -> `n+10` called
    # as a function -> "int object is not callable".
    run_cell(
        "result = [0, 1, 2] |> map{\n"
        "    doubled = $ * 2\n"
        "    doubled |> $ + 10\n"
        "} |> list"
    )
    assert result() == [10, 12, 14], result()


# ---------------------------------------------------------------------------
# Dynamic *method* macros (``obj.foreach[...]``, ``obj.foreach{...}``).
#
# A method macro's template (e.g. ``foreach = method[$$ |> map[do[$$]] |> list]``)
# is defined once and expanded on later cells. Its expansion relies on the
# template still carrying its augmentation marks ($$ placeholders, |> pipe ops,
# nested map/do markers). Those live in pyccolo's process-wide bookkeeping, which
# ``reset_bookkeeping`` wipes wholesale (between cells in this harness) -- after
# which the template expanded to nothing (`Wrong number of arguments: expected 0
# but got 1`, swallowed -> silent no-op). pipescript now latches the template's
# marks durably and re-establishes them per expansion.
# ---------------------------------------------------------------------------


def test_foreach_method_macro_bracket():
    run_cell("out = []\n[0, 1, 2].foreach[do[out.append($)]]\nresult = out")
    assert result() == [0, 1, 2], result()


def test_foreach_method_macro_brace_block():
    run_cell(
        "result = []\n"
        "[0, 1, 2].foreach{\n"
        "    if $ == 0:\n"
        "        result.append('zero')\n"
        "    else:\n"
        "        result.append($ |> $ + 1)\n"
        "}"
    )
    assert result() == ["zero", 2, 3], result()


def test_custom_method_macro_reused_across_cells():
    run_cell("twice = method[$$ |> map[$$] |> list]")
    run_cell("result = [1, 2, 3].twice[$ + 100]")
    assert result() == [101, 102, 103], result()
    run_cell("result = [4, 5].twice[$ * 10]")
    assert result() == [40, 50], result()


# ---------------------------------------------------------------------------
# Macros implemented as Python functions that synchronously call the user's
# placeholder-lambda (fork/parallel/when/unless/do/expect/...). The called
# lambda lives in a pyccolo sandbox, but the macro's own frame sits between it
# and the cell; unless that frame is marked hidden, ipyflow's get_position stops
# there and maps the static_macros source line onto the executing cell, raising
# in _get_stmt_node_for_sys_event. (Macros backed by C builtins like map/filter
# never hit this -- there is no intervening Python frame.) These exercise the
# `__hide_pyccolo_frame__` markers on those functions.
# ---------------------------------------------------------------------------


def test_fork():
    run_cell("result = 5 |> fork[$ + 1, $ * 2]")
    assert result() == (6, 10), result()


def test_parallel():
    run_cell("result = 5 |> parallel[$ + 1, $ * 2]")
    assert result() == (6, 10), result()


def test_when_passes_through():
    run_cell("result = 5 |> when[$ > 0]")
    assert result() == 5, result()


def test_unless_passes_through():
    run_cell("result = 5 |> unless[$ < 0]")
    assert result() == 5, result()


def test_until_passes_through():
    run_cell("result = 5 |> until[$ < 0]")
    assert result() == 5, result()


def test_expect_passes_through():
    run_cell("result = 5 |> expect[$ > 0]")
    assert result() == 5, result()


def test_do_side_effect():
    run_cell("out = []\n5 |> do[out.append($ * 2)]\nresult = out")
    assert result() == [10], result()


def test_brace_fork_tuple():
    run_cell("result = 5 |> fork{ $ + 1, $ * 2 }")
    assert result() == (6, 10), result()


# ---------------------------------------------------------------------------
# Placeholder liveness
#
# pipescript rewrites its ``$`` / ``$$`` placeholders to ``_`` (and ``$foo`` to
# ``_foo``) in the cell source. These synthetic names must not be picked up by
# ipyflow's liveness analyzer as references to the IPython ``_`` (last-expr)
# symbol, or every placeholder cell would spuriously depend on whatever the
# previous cell evaluated to. We assert liveness statically (no execution, so
# the dataflow tracer's synthetic lambda line numbers are not involved).
# ---------------------------------------------------------------------------


def _live_ref_strs(code):
    cell = Cell.create_and_track(object(), code, (), bump_cell_counter=False)
    live, *_ = cell._get_live_dead_modified_symbol_refs(False)
    return {str(ref.ref) for ref in live}


@pytest.mark.parametrize(
    "code",
    [
        "reverse_sorter = sorted($, reverse=True)",
        "sorter = sorted($, reverse=$)",
        "result = lst |> sorted($, reverse=True)",
        "result = lst |> $.index(3)",
        "result = data |> np.max($, initial=1.0)",
        "result = 42 |> $ + 1",
        "result = f[$ + $](2, 3)",
        "result = f[$a*$b](2, 3)",
    ],
)
def test_placeholder_not_live(code):
    # ``_`` (and named placeholders like ``_a``) should never appear as live.
    assert not any(
        ref == "('_',)" or ref.startswith("('_'") or ref.startswith("('_a'")
        for ref in _live_ref_strs(code)
    ), _live_ref_strs(code)


def test_real_refs_preserved_alongside_placeholders():
    # the placeholder is dropped, but genuine references in the same cell remain.
    live = _live_ref_strs("result = lst |> sorted($, key=mykey)")
    assert "('lst',)" in live
    assert "('mykey',)" in live
    assert "('_',)" not in live


def test_placeholder_not_live_after_marks_discarded():
    # pipescript discards a node's pyccolo augmentation marks once it rewrites
    # the placeholder during execution. ipyflow latches the placeholder status
    # when it first builds the cell AST, so the ``_`` must stay excluded from
    # liveness even after the marks are gone -- otherwise the spurious dependency
    # on the previous cell's ``_`` reappears on subsequent frontend re-checks.
    import pyccolo as pyc

    cell = Cell.create_and_track(
        object(),
        "reverse_sorter = sorted($, reverse=True)",
        (),
        bump_cell_counter=False,
    )
    live_before, *_ = cell._get_live_dead_modified_symbol_refs(False)
    assert not any(str(r.ref).startswith("('_'") for r in live_before)
    # simulate pipescript clearing the augmentation marks post-rewrite
    for ids in pyc.BaseTracer.augmented_node_ids_by_spec.values():
        ids.clear()
    live_after, *_ = cell._get_live_dead_modified_symbol_refs(False)
    assert not any(str(r.ref).startswith("('_'") for r in live_after), {
        str(r.ref) for r in live_after
    }


def test_placeholder_not_live_after_intervening_executions():
    # the "takes a few executions" scenario: executing other placeholder cells
    # churns pyccolo's process-wide augmentation bookkeeping, but a freshly
    # built placeholder cell must still exclude ``_`` from liveness.
    run_cell("result = f[$ + $](2, 3)")
    run_cell("x = 5")
    run_cell("result = f[$a*$b + $b*$c + $a*$c](2, 3, 4)")
    cell = Cell.create_and_track(
        object(), "result = 42 |> $ + 1", (), bump_cell_counter=False
    )
    live, *_ = cell._get_live_dead_modified_symbol_refs(False)
    assert not any(str(r.ref).startswith("('_'") for r in live), {
        str(r.ref) for r in live
    }


def test_pipescript_block_traceback_diagnosis_and_pinpointing():
    # A `fork` branch that *applies* (`|> all`) where it must *compose* (`.> all`)
    # leaks a stage-function into `all(...)`. End-to-end under ipyflow we expect:
    # the diagnostic notes (apply-vs-compose hint + which branch), and a visible,
    # meaningfully-named block frame that pinpoints the failing stage's source.
    run_cell(
        "import traceback as _tb\n"
        "try:\n"
        "    result = ['aaa', 'bbb'] |> map{\n"
        "        ok = $ |> fork[ map[$v in 'aeiou'] .> any, map[$ in 'aeiou'] |> all ] |> all\n"
        "        ok\n"
        "    } |> sum\n"
        "except Exception as _e:\n"
        "    _notes = list(getattr(_e, '_pyc_notes', []))\n"
        "    _frames = [\n"
        "        (f.f_code.co_name, f.f_code.co_filename)\n"
        "        for f, _ in _tb.walk_tb(_e.__traceback__)\n"
        "    ]\n"
    )
    import pyccolo as pyc

    notes = shell().user_ns["_notes"]
    assert any("fork branch #2 of 2" in n for n in notes), notes
    assert any(".>" in n and "compose" in n for n in notes), notes
    # the block frame is meaningfully named and kept visible by ipyflow's filter
    frames = shell().user_ns["_frames"]
    assert any(
        name == "map{...}" and pyc.is_traceback_visible(fname) for name, fname in frames
    ), frames
