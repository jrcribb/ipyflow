# -*- coding: utf-8 -*-
import logging
from collections import defaultdict
from typing import Any, Dict, List, Iterable, NamedTuple, Optional, Set, Tuple

from ipyflow.data_model.code_cell import cells, CheckerResult, ExecutedCodeCell
from ipyflow.data_model.data_symbol import DataSymbol
from ipyflow.run_mode import ExecutionMode, ExecutionSchedule, FlowDirection
from ipyflow.singletons import flow
from ipyflow.types import CellId


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class FrontendCheckerResult(NamedTuple):
    waiting_cells: Set[CellId]
    ready_cells: Set[CellId]
    new_ready_cells: Set[CellId]
    forced_reactive_cells: Set[CellId]
    typecheck_error_cells: Set[CellId]
    unsafe_order_cells: Dict[CellId, Set[ExecutedCodeCell]]
    waiter_links: Dict[CellId, Set[CellId]]
    ready_maker_links: Dict[CellId, Set[CellId]]
    phantom_cell_info: Dict[CellId, Dict[CellId, Set[int]]]

    @classmethod
    def empty(cls):
        return cls(
            waiting_cells=set(),
            ready_cells=set(),
            new_ready_cells=set(),
            forced_reactive_cells=set(),
            typecheck_error_cells=set(),
            unsafe_order_cells=defaultdict(set),
            waiter_links=defaultdict(set),
            ready_maker_links=defaultdict(set),
            phantom_cell_info={},
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            # TODO: we should probably have separate fields for waiting vs non-typechecking cells,
            #  or at least change the name to a more general "unsafe_cells" or equivalent
            "waiting_cells": list(self.waiting_cells | self.typecheck_error_cells),
            "ready_cells": list(self.ready_cells),
            "new_ready_cells": list(self.new_ready_cells),
            "forced_reactive_cells": list(self.forced_reactive_cells),
            "waiter_links": {
                cell_id: list(linked_cell_ids)
                for cell_id, linked_cell_ids in self.waiter_links.items()
            },
            "ready_maker_links": {
                cell_id: list(linked_cell_ids)
                for cell_id, linked_cell_ids in self.ready_maker_links.items()
            },
        }

    def _compute_waiter_and_ready_maker_links(self) -> None:
        waiter_link_changes = True
        # transitive closure up until we hit non-waiting ready-making cells
        while waiter_link_changes:
            waiter_link_changes = False
            for waiting_cell_id in self.waiting_cells:
                new_waiter_links = set(self.waiter_links[waiting_cell_id])
                original_length = len(new_waiter_links)
                for ready_making_cell_id in self.waiter_links[waiting_cell_id]:
                    if ready_making_cell_id not in self.waiting_cells:
                        continue
                    new_waiter_links |= self.waiter_links[ready_making_cell_id]
                new_waiter_links.discard(waiting_cell_id)
                waiter_link_changes = waiter_link_changes or original_length != len(
                    new_waiter_links
                )
                self.waiter_links[waiting_cell_id] = new_waiter_links
        for waiting_cell_id in self.waiting_cells:
            self.waiter_links[waiting_cell_id] -= self.waiting_cells
            for ready_making_cell_id in self.waiter_links[waiting_cell_id]:
                self.ready_maker_links[ready_making_cell_id].add(waiting_cell_id)

    def _compute_ready_making_cells(
        self,
        waiting_symbols_by_cell_id: Dict[CellId, Set[DataSymbol]],
        killing_cell_ids_for_symbol: Dict[DataSymbol, Set[CellId]],
        last_executed_cell_id: Optional[CellId],
    ) -> None:
        flow_ = flow()
        eligible_ready_making_for_dag = self.ready_cells | self.waiting_cells
        for waiting_cell_id in self.waiting_cells:
            ready_making_cell_ids: Set[CellId] = set()
            if flow_.mut_settings.flow_order == ExecutionSchedule.DAG_BASED:
                if flow_.mut_settings.dynamic_slicing_enabled:
                    ready_making_cell_ids |= (
                        cells().from_id(waiting_cell_id).dynamic_parent_ids
                        & eligible_ready_making_for_dag
                    )
                if flow_.mut_settings.static_slicing_enabled:
                    ready_making_cell_ids |= (
                        cells().from_id(waiting_cell_id).static_parent_ids
                        & eligible_ready_making_for_dag
                    )
            else:
                waiting_syms = waiting_symbols_by_cell_id.get(waiting_cell_id, set())
                ready_making_cell_ids = ready_making_cell_ids.union(
                    *(
                        killing_cell_ids_for_symbol[waiting_sym]
                        for waiting_sym in waiting_syms
                    )
                )
            if flow_.mut_settings.flow_order == FlowDirection.IN_ORDER:
                ready_making_cell_ids = {
                    cid
                    for cid in ready_making_cell_ids
                    if cells().from_id(cid).position
                    < cells().from_id(waiting_cell_id).position
                }
            if last_executed_cell_id is not None:
                ready_making_cell_ids.discard(last_executed_cell_id)
            self.waiter_links[waiting_cell_id] = ready_making_cell_ids

    def _compute_reactive_cells_for_reactive_symbols(
        self, checker_results_by_cid: Dict[CellId, CheckerResult]
    ) -> None:
        flow_ = flow()
        if flow_.mut_settings.exec_mode == ExecutionMode.REACTIVE:
            # no need to do this computation if already in reactive mode, since
            # everything that is new ready is automatically considered reactive
            return
        for cell_id in self.ready_cells:
            if cell_id not in checker_results_by_cid:
                continue
            cell = cells().from_id(cell_id)
            max_used_ctr = cell.get_max_used_live_symbol_cell_counter(
                checker_results_by_cid[cell_id].live, filter_to_reactive=True
            )
            if max_used_ctr > max(cell.cell_ctr, flow_.min_timestamp):
                self.forced_reactive_cells.add(cell_id)

    def _compute_dag_based_waiters(
        self, cells_to_check: List[ExecutedCodeCell]
    ) -> None:
        flow_ = flow()
        if flow_.mut_settings.exec_schedule != ExecutionSchedule.DAG_BASED:
            return
        prev_waiting_cells: Set[CellId] = set()
        while True:
            for cell in cells_to_check:
                if cell.cell_id in self.waiting_cells:
                    continue
                if flow_.mut_settings.dynamic_slicing_enabled:
                    if cell.dynamic_parent_ids & (
                        self.ready_cells | self.waiting_cells
                    ):
                        self.waiting_cells.add(cell.cell_id)
                        continue
                if flow_.mut_settings.static_slicing_enabled:
                    if cell.static_parent_ids & (self.ready_cells | self.waiting_cells):
                        self.waiting_cells.add(cell.cell_id)
            if prev_waiting_cells == self.waiting_cells:
                break
            prev_waiting_cells = set(self.waiting_cells)
        self.ready_cells.difference_update(self.waiting_cells)
        self.new_ready_cells.difference_update(self.waiting_cells)
        for cell_id in self.waiting_cells:
            cells().from_id(cell_id).set_ready(False)

    def _compute_is_ready(
        self, cell: ExecutedCodeCell, checker_result: CheckerResult
    ) -> bool:
        flow_ = flow()
        cell_id = cell.cell_id
        is_ready = cell_id not in self.waiting_cells
        if flow_.mut_settings.exec_schedule == ExecutionSchedule.DAG_BASED:
            is_ready = False
            flow_order = flow_.mut_settings.flow_order
            if flow_.mut_settings.dynamic_slicing_enabled:
                for par in cell.dynamic_parents:
                    if (
                        flow_order == flow_order.IN_ORDER
                        and par.position >= cell.position
                    ):
                        continue
                    if par.cell_ctr > max(cell.cell_ctr, flow_.min_timestamp):
                        is_ready = True
                        break
            if not is_ready and flow_.mut_settings.static_slicing_enabled:
                for par in cell.static_parents:
                    if (
                        flow_order == flow_order.IN_ORDER
                        and par.position >= cell.position
                    ):
                        continue
                    if par.cell_ctr > max(cell.cell_ctr, flow_.min_timestamp):
                        is_ready = True
                        break
        else:
            is_ready = is_ready and (
                cell.get_max_used_live_symbol_cell_counter(checker_result.live)
                > max(cell.cell_ctr, flow_.min_timestamp)
            )
        if flow_.mut_settings.exec_schedule == ExecutionSchedule.STRICT:
            for dead_sym in checker_result.dead:
                if dead_sym.timestamp.cell_num > max(
                    cell.cell_ctr, flow_.min_timestamp
                ):
                    is_ready = True
        return is_ready

    def _check_one_cell(
        self,
        cell: ExecutedCodeCell,
        update_liveness_time_versions: bool,
        last_executed_cell_pos: int,
        waiting_symbols_by_cell_id: Dict[CellId, Set[DataSymbol]],
        killing_cell_ids_for_symbol: Dict[DataSymbol, Set[CellId]],
        phantom_cell_info: Dict[CellId, Dict[CellId, Set[int]]],
    ) -> Optional[CheckerResult]:
        flow_ = flow()
        try:
            checker_result = cell.check_and_resolve_symbols(
                update_liveness_time_versions=update_liveness_time_versions
            )
        except SyntaxError:
            return None
        cell_id = cell.cell_id
        if (
            flow_.mut_settings.flow_order == FlowDirection.IN_ORDER
            or flow_.mut_settings.exec_schedule == ExecutionSchedule.STRICT
        ):
            for live_sym in checker_result.live:
                if not live_sym.is_deep or not live_sym.timestamp.is_initialized:
                    continue
                updated_cell = cells().from_timestamp(live_sym.timestamp)
                if updated_cell.position > cell.position:
                    self.unsafe_order_cells[cell_id].add(updated_cell)
        if flow_.mut_settings.flow_order == FlowDirection.IN_ORDER:
            if (
                last_executed_cell_pos is not None
                and cell.position <= last_executed_cell_pos
            ):
                return checker_result
        if flow_.mut_settings.exec_schedule == ExecutionSchedule.LIVENESS_BASED:
            waiting_symbols = {
                sym.dsym
                for sym in checker_result.live
                if sym.is_waiting_at_position(cell.position)
            }
        else:
            waiting_symbols = set()
        if len(waiting_symbols) > 0:
            waiting_symbols_by_cell_id[cell_id] = waiting_symbols
            self.waiting_cells.add(cell_id)
        if not checker_result.typechecks:
            self.typecheck_error_cells.add(cell_id)
        for dead_sym in checker_result.dead:
            killing_cell_ids_for_symbol[dead_sym].add(cell_id)

        if flow_.settings.mark_phantom_cell_usages_unsafe:
            phantom_cell_info_for_cell = cell.compute_phantom_cell_info(
                checker_result.used_cells
            )
            if len(phantom_cell_info_for_cell) > 0:
                phantom_cell_info[cell_id] = phantom_cell_info_for_cell
        is_ready = self._compute_is_ready(cell, checker_result)
        if is_ready:
            self.ready_cells.add(cell_id)
        if not cells().from_id(cell_id).set_ready(is_ready) and is_ready:
            self.new_ready_cells.add(cell_id)
        return checker_result

    def _get_last_executed_pos_and_handle_reactive_tags(
        self,
        last_executed_cell_id: Optional[CellId],
    ) -> Optional[int]:
        if last_executed_cell_id is None:
            return None
        last_executed_cell = cells().from_id(last_executed_cell_id)
        if last_executed_cell is None:
            return None
        for tag in last_executed_cell.tags:
            for reactive_cell_id in cells().get_reactive_ids_for_tag(tag):
                self.forced_reactive_cells.add(reactive_cell_id)
        return last_executed_cell.position

    def compute_frontend_checker_result(
        self,
        cells_to_check: Optional[Iterable[ExecutedCodeCell]] = None,
        update_liveness_time_versions: bool = False,
        last_executed_cell_id: Optional[CellId] = None,
    ) -> "FrontendCheckerResult":
        flow_ = flow()
        waiting_symbols_by_cell_id: Dict[CellId, Set[DataSymbol]] = {}
        killing_cell_ids_for_symbol: Dict[DataSymbol, Set[CellId]] = defaultdict(set)
        phantom_cell_info: Dict[CellId, Dict[CellId, Set[int]]] = {}
        checker_results_by_cid: Dict[CellId, CheckerResult] = {}
        last_executed_cell_pos = self._get_last_executed_pos_and_handle_reactive_tags(
            last_executed_cell_id
        )
        if cells_to_check is None:
            cells_to_check = cells().all_cells_most_recently_run_for_each_id()
        cells_to_check = sorted(cells_to_check, key=lambda c: c.position)
        for cell in cells_to_check:
            checker_result = self._check_one_cell(
                cell,
                update_liveness_time_versions,
                last_executed_cell_pos,
                waiting_symbols_by_cell_id,
                killing_cell_ids_for_symbol,
                phantom_cell_info,
            )
            if checker_result is not None:
                checker_results_by_cid[cell.cell_id] = checker_result
            if (
                flow_.mut_settings.exec_schedule == ExecutionSchedule.STRICT
                and cell.is_ready
            ):
                # in the case of strict scheduling, don't bother checking
                # anything else once we get to the first ready cell
                break

        self._compute_dag_based_waiters(cells_to_check)
        self._compute_reactive_cells_for_reactive_symbols(checker_results_by_cid)
        self._compute_ready_making_cells(
            waiting_symbols_by_cell_id,
            killing_cell_ids_for_symbol,
            last_executed_cell_id,
        )
        self._compute_waiter_and_ready_maker_links()
        return self