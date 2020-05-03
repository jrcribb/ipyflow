# -*- coding: utf-8 -*-
from __future__ import annotations

from nbsafety.analysis.edges import get_edge_lvals_and_rvals
from nbsafety.analysis.lineno_stmt_map import compute_lineno_to_stmt_mapping


def test_for_loop():
    code = """
for i in range(10):
    a = i
    b = a + i
    lst = [a, b]
""".strip()
    mapping = compute_lineno_to_stmt_mapping(code)
    lvals, rvals = get_edge_lvals_and_rvals(mapping[1])
    assert lvals == {'i'}
    assert rvals == {'range'}
    lvals, rvals = get_edge_lvals_and_rvals(mapping[2])
    assert lvals == {'a'}
    assert rvals == {'i'}
    lvals, rvals = get_edge_lvals_and_rvals(mapping[3])
    assert lvals == {'b'}
    assert rvals == {'a', 'i'}
    lvals, rvals = get_edge_lvals_and_rvals(mapping[4])
    assert lvals == {'lst'}
    assert rvals == {'a', 'b'}


def test_context_manager():
    code = """
fname = 'file.txt'
with open(fname) as f:
    contents = f.read()
""".strip()
    mapping = compute_lineno_to_stmt_mapping(code)
    lvals, rvals = get_edge_lvals_and_rvals(mapping[2])
    print(lvals)
    print(rvals)
    assert lvals == {'f'}
    assert rvals == {'fname', 'open'}
    lvals, rvals = get_edge_lvals_and_rvals(mapping[3])
    assert lvals == {'contents'}
    assert rvals == {'f'}
