# -*- coding: utf-8 -*-
from __future__ import annotations
import ast
from typing import TYPE_CHECKING

from ..analysis import get_hyperedge_lvals_and_rvals
from ..data_cell import FunctionDataCell

if TYPE_CHECKING:
    from typing import Optional, Set
    from ..data_cell import DataCell
    from ..safety import DependencySafety


class CodeLine(object):
    def __init__(self, safety: DependencySafety, text, ast_node: Optional[ast.AST], lineno, scope):
        self.safety = safety
        self.text = text
        self.ast_node = ast_node
        self.lineno = lineno
        self.scope = scope
        self.extra_dependencies: Set[DataCell] = set()

    def compute_rval_dependencies(self, rval_names=None):
        if rval_names is None:
            _, rval_names = get_hyperedge_lvals_and_rvals(self.ast_node)
        rval_data_cells = set()
        for name in rval_names:
            maybe_rval_dc = self.scope.lookup_data_cell_by_name(name)
            if maybe_rval_dc is not None:
                rval_data_cells.add(maybe_rval_dc)
        return rval_data_cells | self.extra_dependencies

    def get_post_call_scope(self, old_scope):
        if not isinstance(self.ast_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # TODO: the correct check is whether a lambda appears somewhere inside the ast node
            # if not isinstance(self.ast_node, ast.Lambda):
            #     raise TypeError('unexpected type for ast node %s' % self.ast_node)
            return old_scope
        func_name = self.ast_node.name
        func_cell = self.scope.lookup_data_cell_by_name(func_name)
        if func_cell is None:
            # TODO: brittle; assumes any user-defined and traceable function will always be present; is this safe?
            return old_scope
        if not isinstance(func_cell, FunctionDataCell):
            raise TypeError('got non-function data cell for name %s' % func_name)
        return func_cell.scope

    def make_lhs_data_cells_if_has_lval(self):
        if not self.has_lval:
            return
        if not self.safety.dependency_tracking_enabled:
            return
        lval_names, rval_names = get_hyperedge_lvals_and_rvals(self.ast_node)
        rval_deps = self.compute_rval_dependencies(rval_names=rval_names-lval_names)
        is_function_def = isinstance(self.ast_node, (ast.FunctionDef, ast.AsyncFunctionDef))
        should_add = isinstance(self.ast_node, ast.AugAssign)
        if is_function_def:
            assert len(lval_names) == 1
            assert not lval_names.issubset(rval_names)
        for name in lval_names:
            should_add_for_name = should_add or name in rval_names
            self.scope.upsert_data_cell_for_name(
                name, rval_deps, add=should_add_for_name, is_function_def=is_function_def
            )

    @property
    def has_lval(self):
        # TODO: expand to method calls, etc.
        return isinstance(self.ast_node, (
            ast.Assign, ast.AugAssign, ast.FunctionDef, ast.AsyncFunctionDef, ast.For
        ))
