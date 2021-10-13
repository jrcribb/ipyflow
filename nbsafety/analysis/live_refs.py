# -*- coding: future_annotations -*-
import ast
import logging
from typing import cast, TYPE_CHECKING

from nbsafety.analysis.symbol_ref import get_attrsub_symbol_chain, SymbolRef, Atom
from nbsafety.analysis.live_symbols import LiveSymbolRef
from nbsafety.analysis.mixins import SaveOffAttributesMixin, SkipUnboundArgsMixin, VisitListsMixin
from nbsafety.data_model.timestamp import Timestamp
from nbsafety.run_mode import ExecutionMode, FlowOrder
from nbsafety.singletons import nbs
from nbsafety.tracing.mutation_event import resolve_mutating_method

if TYPE_CHECKING:
    from typing import Generator, Iterable, List, Optional, Set, Tuple, Union
    from nbsafety.types import SupportedIndexType
    from nbsafety.data_model.data_symbol import DataSymbol
    from nbsafety.data_model.scope import Scope

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


# TODO: have the logger warnings additionally raise exceptions for tests
class ComputeLiveSymbolRefs(SaveOffAttributesMixin, SkipUnboundArgsMixin, VisitListsMixin, ast.NodeVisitor):
    def __init__(self, scope: Optional[Scope] = None, init_killed: Optional[Set[str]] = None) -> None:
        self._scope = scope
        self._module_stmt_counter = 0
        # live symbols also include the stmt counter of when they were live, for slicing purposes later
        self.live: Set[LiveSymbolRef] = set()
        if init_killed is None:
            self.dead: Set[SymbolRef] = set()
        else:
            self.dead = cast('Set[SymbolRef]', init_killed)
        # TODO: use the ast context instead of hacking our own (e.g. ast.Load(), ast.Store(), etc.)
        self._in_kill_context = False
        self._inside_attrsub = False
        self._skip_simple_names = False

    def __call__(self, node: ast.AST) -> Tuple[Set[LiveSymbolRef], Set[SymbolRef]]:
        """
        This function should be called when we want to do a liveness check on a
        cell's corresponding ast.Module.
        """
        # TODO: this will break if we ref a variable in a loop before killing it in the
        #   same loop, since we will add everything on the LHS of an assignment to the killed
        #   set before checking the loop body for live variables
        self.visit(node)
        return self.live, self.dead

    def kill_context(self):
        return self.push_attributes(_in_kill_context=True)

    def live_context(self):
        return self.push_attributes(_in_kill_context=False)

    def attrsub_context(self, inside=True):
        return self.push_attributes(_inside_attrsub=inside, _skip_simple_names=inside)

    def args_context(self):
        return self.push_attributes(_skip_simple_names=False)

    def _add_attrsub_to_live_if_eligible(self, ref: SymbolRef) -> None:
        if ref.nonreactive() in self.dead:
            return
        if len(ref.chain) == 0:
            # can happen if user made syntax error like [1, 2, 3][4, 5, 6] (e.g. forgot comma)
            return
        leading_atom = ref.chain[0]
        if isinstance(leading_atom.value, str):
            if SymbolRef(leading_atom) in self.dead or SymbolRef(Atom(leading_atom.value, is_callpoint=False)) in self.dead:
                return
        self.live.add(LiveSymbolRef(ref, self._module_stmt_counter))

    # the idea behind this one is that we don't treat a symbol as dead
    # if it is used on the RHS of an assignment
    def visit_Assign_impl(self, targets, value, aug_assign_target=None) -> None:
        this_assign_live: Set[LiveSymbolRef] = set()
        # we won't mutate overall dead for visiting simple targets, and we need it to avoid adding false positive lives
        with self.push_attributes(live=this_assign_live):
            self.visit(value)
            if aug_assign_target is not None:
                self.visit(aug_assign_target)
        # make a copy, then track the new dead
        this_assign_dead = set(self.dead)
        with self.push_attributes(dead=this_assign_dead):
            with self.kill_context():
                for target in targets:
                    self.visit_Assign_target(target)
        this_assign_dead -= self.dead
        # TODO: ideally under the current abstraction we should
        #  not be resolving static references to symbols here
        if (
            nbs().mut_settings.flow_order == FlowOrder.ANY_ORDER
            and self._scope is not None
            and len(this_assign_live) == 1
            and len(this_assign_dead) == 1
            and not (this_assign_dead <= self.dead)
            and aug_assign_target is None
            and isinstance(value, (ast.Attribute, ast.Subscript, ast.Name))
        ):
            lhs, rhs = [
                get_symbols_for_references(x, self._scope, only_yield_successful_resolutions=True)[0]
                for x in (this_assign_dead, (live.ref for live in this_assign_live))
            ]
            if len(lhs) == 1 and len(rhs) == 1:
                syms: List[DataSymbol] = [next(iter(x)) for x in (lhs, rhs)]
                lhs_sym, rhs_sym = syms[0], syms[1]
                # hack to avoid marking `b` as live when objects are same,
                # or when it was detected that rhs symbol wasn't actually updated
                if lhs_sym.obj is rhs_sym.obj or lhs_sym.timestamp_excluding_ns_descendents > rhs_sym.timestamp:
                    # either (a) it's a no-op (so treat it as such), or
                    #        (b) lhs is newer and it doesn't make sense to refresh
                    this_assign_live.clear()
        this_assign_dead -= {live.ref for live in this_assign_live}
        # for ref in this_assign_dead:
        #     if isinstance(ref, AttrSubSymbolChain) and len(ref.symbols) > 1:
        #         this_assign_live.add(
        #             (AttrSubSymbolChain(list(ref.symbols[:-1]) + [
        #                 # FIXME: hack to ensure it can't be resolved all the way, so that we use
        #                 #  timestamp_excluding_ns_children instead of timestamp
        #                 CallPoint('<dummy>')
        #             ]), self._module_stmt_counter)
        #         )
        self.live |= this_assign_live
        self.dead |= this_assign_dead

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.visit_Assign_impl([node.target], node.value)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit_Assign_impl(node.targets, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.visit_Assign_impl([node.target], node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit_Assign_impl([], node.value, aug_assign_target=node.target)

    def visit_Assign_target(
        self, target_node: Union[ast.Attribute, ast.Name, ast.Subscript, ast.Tuple, ast.List, ast.expr]
    ) -> None:
        if isinstance(target_node, (ast.Name, ast.Attribute, ast.Subscript)):
            self.dead.add(get_attrsub_symbol_chain(target_node))
            if isinstance(target_node, ast.Subscript):
                with self.live_context():
                    self.visit(target_node.slice)
        elif isinstance(target_node, (ast.Tuple, ast.List)):
            for elt in target_node.elts:
                self.visit_Assign_target(elt)
        elif isinstance(target_node, ast.Starred):
            self.visit_Assign_target(target_node.value)
        else:
            logger.warning('unsupported type for node %s' % target_node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.generic_visit(node.args.defaults)
        self.generic_visit(node.decorator_list)
        self.dead.add(SymbolRef(node.name))

    def visit_Name(self, node: ast.Name) -> None:
        ref = SymbolRef(node.id)
        if self._in_kill_context:
            self.dead.add(ref)
        elif not self._skip_simple_names and ref not in self.dead:
            if id(node) in nbs().reactive_variable_node_ids:
                ref.chain[0].is_reactive = True
            self.live.add(LiveSymbolRef(ref, self._module_stmt_counter))

    def visit_Tuple_or_List(self, node: Union[ast.List, ast.Tuple]) -> None:
        for elt in node.elts:
            self.visit(elt)

    def visit_List(self, node: ast.List) -> None:
        self.visit_Tuple_or_List(node)

    def visit_Tuple(self, node: ast.Tuple) -> None:
        self.visit_Tuple_or_List(node)

    def visit_For(self, node: ast.For) -> None:
        # Case "for a,b in something: "
        self.visit(node.iter)
        with self.kill_context():
            self.visit(node.target)
        for line in node.body:
            self.visit(line)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.generic_visit(node.bases)
        self.generic_visit(node.decorator_list)
        self.dead.add(SymbolRef(node.name))

    def visit_Call(self, node: ast.Call) -> None:
        with self.args_context():
            self.generic_visit(node.args)
            for kwarg in node.keywords:
                self.visit(kwarg.value)
        if not self._inside_attrsub:
            self._add_attrsub_to_live_if_eligible(get_attrsub_symbol_chain(node))
        with self.attrsub_context():
            self.visit(node.func)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if not self._inside_attrsub:
            self._add_attrsub_to_live_if_eligible(get_attrsub_symbol_chain(node))
        with self.attrsub_context():
            self.visit(node.value)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if not self._inside_attrsub:
            self._add_attrsub_to_live_if_eligible(get_attrsub_symbol_chain(node))
        with self.attrsub_context():
            self.visit(node.value)
        with self.attrsub_context(inside=False):
            self.visit(node.slice)

    def visit_Delete(self, node: ast.Delete) -> None:
        pass

    def visit_GeneratorExp(self, node) -> None:
        self.visit_GeneratorExp_or_DictComp_or_ListComp_or_SetComp(node)

    def visit_DictComp(self, node) -> None:
        self.visit_GeneratorExp_or_DictComp_or_ListComp_or_SetComp(node)

    def visit_ListComp(self, node) -> None:
        self.visit_GeneratorExp_or_DictComp_or_ListComp_or_SetComp(node)

    def visit_SetComp(self, node) -> None:
        self.visit_GeneratorExp_or_DictComp_or_ListComp_or_SetComp(node)

    def visit_GeneratorExp_or_DictComp_or_ListComp_or_SetComp(self, node) -> None:
        # TODO: as w/ for loop, this will have false positives on later live references
        for gen in node.generators:
            self.visit(gen.iter)
            with self.kill_context():
                self.visit(gen.target)
        # visit the elt at the end to ensure we don't add it to live vars if it was one of the generator targets
        self.visit(node.elt)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        with self.kill_context():
            self.visit(node.args)

    def visit_arg(self, node) -> None:
        ref = SymbolRef(node.arg)
        if self._in_kill_context:
            self.dead.add(ref)
        elif not self._skip_simple_names and ref not in self.dead:
            self.live.add(LiveSymbolRef(ref, self._module_stmt_counter))

    def visit_Module(self, node: ast.Module) -> None:
        for child in node.body:
            assert isinstance(child, ast.stmt)
            self.visit(child)
            self._module_stmt_counter += 1


def gen_symbols_for_references(
    symbol_refs: Iterable[SymbolRef],
    scope: Scope,
    only_yield_final_symbol: bool,
    yield_all_intermediate_symbols: bool = False,
) -> Generator[Tuple[DataSymbol, Optional[Atom], bool, bool], None, None]:
    assert not (only_yield_final_symbol and yield_all_intermediate_symbols)
    for symbol_ref in symbol_refs:
        if yield_all_intermediate_symbols and not only_yield_final_symbol:
            # TODO: only use this branch one staleness checker can be smarter about liveness timestamps.
            #  Right now, yielding the intermediate elts of the chain will yield false positives in the
            #  event of namespace stale children.
            yield from scope.gen_data_symbols_for_attrsub_chain(symbol_ref)
        else:
            dsym_et_al = scope.get_most_specific_data_symbol_for_attrsub_chain(symbol_ref)
            if dsym_et_al is not None:
                dsym, next_ref, is_called, success = dsym_et_al
                if success or not only_yield_final_symbol:
                    yield dsym, next_ref, is_called, success


def get_symbols_for_references(
    symbol_refs: Iterable[SymbolRef],
    scope: Scope,
    only_yield_successful_resolutions: bool = False,
) -> Tuple[Set[DataSymbol], Set[DataSymbol]]:
    dsyms: Set[DataSymbol] = set()
    called_dsyms: Set[DataSymbol] = set()
    for dsym, is_called, *_ in gen_symbols_for_references(
        symbol_refs, scope, only_yield_final_symbol=only_yield_successful_resolutions
    ):
        if is_called:
            called_dsyms.add(dsym)
        else:
            dsyms.add(dsym)
    return dsyms, called_dsyms


def _live_dsym_is_mutating(dsym: DataSymbol, next_ref: Atom) -> bool:
    assert next_ref.is_callpoint
    return resolve_mutating_method(dsym.obj, cast(str, next_ref.value)) is not None


def _live_dsym_unsafe(dsym: DataSymbol, next_ref: SupportedIndexType) -> bool:
    if isinstance(dsym.obj, (list, tuple)) and isinstance(next_ref, int) and next_ref >= len(dsym.obj):
        return True
    if isinstance(dsym.obj, dict) and next_ref not in dsym.obj:
        return True
    if not isinstance(dsym.obj, (dict, list, tuple)) and isinstance(next_ref, str) and not hasattr(dsym.obj, next_ref):
        # TODO: fix this once we can distinguish between attrs and subscripts in the chain
        return True
    return False


def _handle_live_symbol(
    dsym: DataSymbol,
    next_ref: Optional[Atom],
    deep_live: Set[DataSymbol],
    shallow_live: Set[DataSymbol]
) -> None:
    if next_ref is None:
        deep_live.add(dsym)
    elif not next_ref.is_callpoint:
        if _live_dsym_unsafe(dsym, next_ref.value):
            return
        else:
            shallow_live.add(dsym)
    elif _live_dsym_is_mutating(dsym, next_ref):  # isinstance(next_ref, CallPoint)
        if nbs().mut_settings.exec_mode == ExecutionMode.NORMAL:
            shallow_live.add(dsym)
        elif nbs().mut_settings.exec_mode == ExecutionMode.REACTIVE:
            return
        else:
            raise ValueError('not sure how to handle execution mode %s' % nbs().mut_settings.exec_mode)
    else:
        deep_live.add(dsym)


def get_live_symbols_and_cells_for_references(
    symbol_refs: Set[LiveSymbolRef],
    scope: Scope,
    cell_ctr: int,
    update_liveness_time_versions: bool = False,
) -> Tuple[Set[DataSymbol], Set[DataSymbol], Set[int]]:
    deep_live_dsyms: Set[DataSymbol] = set()
    shallow_live_dsyms: Set[DataSymbol] = set()
    called_dsyms: Set[Tuple[DataSymbol, int]] = set()
    for live_symbol_ref in symbol_refs:
        for dsym, next_ref, is_called, success in gen_symbols_for_references(
            [live_symbol_ref.ref],
            scope,
            only_yield_final_symbol=False,
            yield_all_intermediate_symbols=update_liveness_time_versions,
        ):
            if update_liveness_time_versions:
                ts_to_use = dsym.timestamp if success else dsym.timestamp_excluding_ns_descendents
                liveness_time = Timestamp(cell_ctr, live_symbol_ref.timestamp)
                assert liveness_time > ts_to_use
                if ts_to_use.is_initialized:
                    nbs().add_static_data_dep(liveness_time, ts_to_use)
                    dsym.timestamp_by_liveness_time[liveness_time] = ts_to_use
            if is_called:
                called_dsyms.add((dsym, live_symbol_ref.timestamp))
            else:
                _handle_live_symbol(dsym, next_ref, deep_live_dsyms, shallow_live_dsyms)
    deep_live_from_calls, shallow_live_from_calls, live_cells = _compute_call_chain_live_symbols_and_cells(
        called_dsyms, cell_ctr, update_liveness_time_versions
    )
    deep_live_dsyms |= deep_live_from_calls
    shallow_live_dsyms |= shallow_live_from_calls
    return deep_live_dsyms, shallow_live_dsyms, live_cells


def _compute_call_chain_live_symbols_and_cells(
    live_with_stmt_ctr: Set[Tuple[DataSymbol, int]], cell_ctr: int, update_liveness_time_versions: bool
) -> Tuple[Set[DataSymbol], Set[DataSymbol], Set[int]]:
    seen = set()
    worklist = list(live_with_stmt_ctr)
    deep_live = {dsym_stmt[0] for dsym_stmt in live_with_stmt_ctr}
    shallow_live: Set[DataSymbol] = set()
    while len(worklist) > 0:
        workitem = worklist.pop()
        if workitem in seen:
            continue
        called_dsym, stmt_ctr = workitem
        # TODO: handle callable classes
        if not called_dsym.is_function:
            continue
        seen.add(workitem)
        live_refs, _ = compute_live_dead_symbol_refs(
            cast(ast.FunctionDef, called_dsym.stmt_node).body, init_killed=set(called_dsym.get_definition_args())
        )
        used_time = Timestamp(cell_ctr, stmt_ctr)
        for dsym, next_ref, is_called, success, *_ in gen_symbols_for_references(
            (ref.ref for ref in live_refs), called_dsym.call_scope, only_yield_final_symbol=False
        ):
            if is_called:
                worklist.append((dsym, stmt_ctr))
            if dsym.is_globally_accessible:
                _handle_live_symbol(dsym, next_ref, deep_live, shallow_live)
                if update_liveness_time_versions:
                    ts_to_use = dsym.timestamp if success else dsym.timestamp_excluding_ns_descendents
                    dsym.timestamp_by_liveness_time[used_time] = ts_to_use
    return deep_live, shallow_live, {called_dsym.timestamp.cell_num for called_dsym, _ in seen}


def compute_live_dead_symbol_refs(
    code: Union[ast.AST, List[ast.stmt], str],
    scope: Scope = None,
    init_killed: Optional[Set[str]] = None,
) -> Tuple[Set[LiveSymbolRef], Set[SymbolRef]]:
    if init_killed is None:
        init_killed = set()
    if isinstance(code, str):
        code = ast.parse(code)
    elif isinstance(code, list):
        code = ast.Module(code)
    return ComputeLiveSymbolRefs(scope=scope, init_killed=init_killed)(code)
