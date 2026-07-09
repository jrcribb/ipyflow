# -*- coding: utf-8 -*-
"""A tracer for ``test_pyccolo_composition``, deliberately defined in a real module.

A tracer defined *in a cell* has its handler's code object attributed to that
cell's filename, so ipyflow's dataflow tracer follows ``sys.settrace`` into it and
trips over statement bookkeeping that only exists for user code. That is a
pre-existing wart, orthogonal to extension composition -- keep it out of the way.
"""
from typing import List

import pyccolo as pyc

hits: List[int] = []


class CountingTracer(pyc.BaseTracer):
    @pyc.before_stmt
    def handle_stmt(self, *_, **__) -> None:
        hits.append(1)
