# -*- coding: utf-8 -*-
from typing import Optional, Union

from ipyflow.data_model.cell import cells
from ipyflow.data_model.timestamp import Timestamp


def _to_cell_num(ts_or_cell_num: Union[int, Timestamp]) -> int:
    return (
        ts_or_cell_num.cell_num
        if isinstance(ts_or_cell_num, Timestamp)
        else ts_or_cell_num
    )


def stdout(ts_or_cell_num: Union[int, Timestamp]) -> Optional[str]:
    """Return the stdout captured during a cell's execution.

    :param ts_or_cell_num: a cell execution counter, or a
        :class:`~ipyflow.data_model.timestamp.Timestamp` (whose ``cell_num`` is
        used).
    :return: the captured stdout as a string, or ``None`` if the cell produced no
        captured output.
    :raises ValueError: if no cell with that counter has executed yet.
    """
    try:
        cell_num = _to_cell_num(ts_or_cell_num)
        captured = cells().at_counter(cell_num).captured_output
        return None if captured is None else str(captured.stdout)
    except KeyError:
        raise ValueError("cell with counter %d has not yet executed" % cell_num)


def stderr(ts_or_cell_num: Union[int, Timestamp]) -> Optional[str]:
    """Return the stderr captured during a cell's execution.

    :param ts_or_cell_num: a cell execution counter, or a
        :class:`~ipyflow.data_model.timestamp.Timestamp` (whose ``cell_num`` is
        used).
    :return: the captured stderr as a string, or ``None`` if the cell produced no
        captured output.
    :raises ValueError: if no cell with that counter has executed yet.
    """
    try:
        cell_num = _to_cell_num(ts_or_cell_num)
        captured = cells().at_counter(cell_num).captured_output
        return None if captured is None else str(captured.stderr)
    except KeyError:
        raise ValueError("cell with counter %d has not yet executed" % cell_num)


def reproduce_cell(
    ctr: int, show_input: bool = True, show_output: bool = True, lookback: int = 0
):
    """Re-render the input and/or output of a previous cell execution.

    Because ipyflow captures each cell's output, this can recover results that
    autosave (for example, a reactive re-run) has since overwritten -- within the
    current kernel session.

    :param ctr: the execution counter of the cell to reproduce.
    :param show_input: whether to render the cell's input source.
    :param show_output: whether to render the cell's captured output.
    :param lookback: how many executions to step back for this cell. ``0`` (the
        default) is the latest execution; ``1`` is the one before it, and so on --
        useful for recovering a result a later re-execution replaced.
    """
    return (
        cells()
        .at_counter(ctr)
        .reproduce(show_input=show_input, show_output=show_output, lookback=lookback)
    )
