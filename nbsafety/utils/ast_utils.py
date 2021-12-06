# -*- coding: future_annotations -*-
import ast
import sys
from typing import TYPE_CHECKING

from nbsafety.extra_builtins import EMIT_EVENT
from nbsafety.tracing.trace_events import TraceEvent
from nbsafety.utils import fast

if TYPE_CHECKING:
    from typing import Dict, FrozenSet, List, Optional, Union


def make_test(var_name: str, negate: bool = False) -> ast.expr:
    ret = fast.parse(f'getattr(builtins, "{var_name}", False)').body[0].value  # type: ignore
    if negate:
        ret = fast.UnaryOp(operand=ret, op=fast.Not())
    return ret


def make_composite_condition(nullable_conditions: List[Optional[ast.expr]], op: Optional[ast.AST] = None):
    conditions = [cond for cond in nullable_conditions if cond is not None]
    if len(conditions) == 1:
        return conditions[0]
    op = op or fast.And()  # type: ignore
    return fast.BoolOp(op=op, values=conditions)


class EmitterMixin:
    def __init__(self, orig_to_copy_mapping: Dict[int, ast.AST], events_with_handlers: FrozenSet[TraceEvent]):
        self.orig_to_copy_mapping = orig_to_copy_mapping
        self.events_with_handlers = events_with_handlers

    def emitter_ast(self):
        return fast.Name(EMIT_EVENT, ast.Load())

    def get_copy_id_ast(self, orig_node_id: Union[int, ast.AST]):
        if not isinstance(orig_node_id, int):
            orig_node_id = id(orig_node_id)
        return fast.Num(id(self.orig_to_copy_mapping[orig_node_id]))

    def emit(self, evt: TraceEvent, node_or_id: Union[int, ast.AST], args=None, **kwargs):
        args = args or []
        return fast.Call(
            func=self.emitter_ast(),
            args=[evt.to_ast(), self.get_copy_id_ast(node_or_id)] + args,
            keywords=fast.kwargs(**kwargs),
        )

    def make_tuple_event_for(self, node: ast.AST, event: TraceEvent, orig_node_id=None, **kwargs):
        if event not in self.events_with_handlers:
            return node
        with fast.location_of(node):
            tuple_node = fast.Tuple(
                [self.emit(event, orig_node_id or node, **kwargs), node],
                ast.Load()
            )
            slc: Union[ast.Constant, ast.Num, ast.Index] = fast.Num(1)
            if sys.version_info < (3, 9):
                slc = fast.Index(slc)
            return fast.Subscript(tuple_node, slc, ast.Load())


def subscript_to_slice(node: ast.Subscript) -> ast.expr:
    if isinstance(node.slice, ast.Index):
        return node.slice.value  # type: ignore
    else:
        return node.slice  # type: ignore
