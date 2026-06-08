# -*- coding: utf-8 -*-
import logging
from test.utils import make_flow_fixture
from typing import Optional, Set, Tuple

from ipyflow.config import ExecutionMode
from ipyflow.data_model.cell import cells
from ipyflow.singletons import flow

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)

# Reset dependency graph before each test
# _flow_fixture, run_cell_ = make_flow_fixture(trace_messages_enabled=True)
_flow_fixture, run_cell_ = make_flow_fixture()


def run_cell(
    cell_content: str, cell_id: Optional[int] = None, ready_are_reactive: bool = False
) -> Tuple[int, Set[int]]:
    orig_mode = flow().mut_settings.exec_mode
    try:
        if ready_are_reactive:
            flow().mut_settings.exec_mode = ExecutionMode.REACTIVE
        executed_cells = set()
        reactive_cells = set()
        next_content_to_run = cell_content
        next_cell_to_run_id = cell_id
        while next_content_to_run is not None:
            executed_cells.add(
                run_cell_(next_content_to_run, cell_id=next_cell_to_run_id)
            )
            if len(executed_cells) == 1:
                cell_id = next(iter(executed_cells))
            next_content_to_run = None
            checker_result = flow().check_and_link_multiple_cells()
            if ready_are_reactive:
                reactive_cells |= checker_result.new_ready_cells
            else:
                reactive_cells |= checker_result.forced_reactive_cells
            for reactive_cell_id in sorted(reactive_cells - executed_cells):
                next_content_to_run = cells().from_id(reactive_cell_id).executed_content
                next_cell_to_run_id = reactive_cell_id
                break
        return cell_id, executed_cells
    finally:
        flow().mut_settings.exec_mode = orig_mode
        flow().comm_manager.handle_reactivity_cleanup()


def run_reactively(
    cell_content: str, cell_id: Optional[int] = None
) -> Tuple[int, Set[int]]:
    return run_cell(cell_content, cell_id=cell_id, ready_are_reactive=True)


# this is working with DAG semantics; need to update tests for that
def test_mutate_one_list_entry():
    assert run_reactively("lst = [1, 2, 3]")[1] == {1}
    assert run_reactively("logging.info(lst[0])")[1] == {2}
    assert run_reactively("logging.info(lst[1])")[1] == {3}
    assert run_reactively("logging.info(lst[2])")[1] == {4}
    for i in range(3):
        cell_id, cells_run = run_reactively(f"lst[{i}] += 1")
        assert cells_run - {cell_id} == {i + 2}, "got %s" % cells_run
    cell_id, cells_run = run_reactively("lst.append(3)")
    assert cells_run - {cell_id} == set(), "got %s" % cells_run
