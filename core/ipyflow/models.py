# -*- coding: utf-8 -*-
from typing import TYPE_CHECKING, List, Optional, Type, Union, overload

from ipyflow.singletons import flow

if TYPE_CHECKING:
    from ipyflow.data_model.cell import Cell
    from ipyflow.data_model.namespace import Namespace
    from ipyflow.data_model.scope import Scope
    from ipyflow.data_model.statement import Statement
    from ipyflow.data_model.symbol import Symbol
    from ipyflow.data_model.timestamp import Timestamp
    from ipyflow.types import IdType


_CodeCellContainer: List[Type["Cell"]] = []
_NamespaceContainer: List[Type["Namespace"]] = []
_ScopeContainer: List[Type["Scope"]] = []
_StatementContainer: List[Type["Statement"]] = []
_SymbolContainer: List[Type["Symbol"]] = []
_TimestampContainer: List[Type["Timestamp"]] = []


if TYPE_CHECKING:

    @overload
    def cells(cell_id: None = None) -> Type["Cell"]:
        ...

    @overload
    def cells(cell_id: "IdType") -> "Cell":
        ...


def cells(cell_id: Optional["IdType"] = None) -> Union[Type["Cell"], "Cell"]:
    """Access the :class:`~ipyflow.data_model.cell.Cell` model.

    Called with no argument, returns the ``Cell`` *class*, whose classmethods
    (``at_counter``, ``from_id``, ``current_cell``, ...) query all cells. Called
    with a ``cell_id`` -- either an execution counter (``int``) or a frontend cell
    id -- returns that specific ``Cell`` instance.
    """
    clazz = _CodeCellContainer[0]
    if cell_id is None:
        return clazz
    elif isinstance(cell_id, int) and cell_id <= clazz.exec_counter():
        return clazz.at_counter(cell_id)
    else:
        return clazz.from_id(cell_id)


def cell_above() -> Optional["Cell"]:
    """Return the cell immediately above the active cell, or ``None``."""
    active_cell_id = flow().active_cell_id
    assert active_cell_id is not None
    return cells().at_position(cells().from_id(active_cell_id).position - 1)


def cell_below() -> Optional["Cell"]:
    """Return the cell immediately below the active cell, or ``None``."""
    active_cell_id = flow().active_cell_id
    assert active_cell_id is not None
    return cells().at_position(cells().from_id(active_cell_id).position + 1)


def cell_at_offset(offset: int) -> Optional["Cell"]:
    """Return the cell ``offset`` positions from the active cell (may be negative)."""
    active_cell_id = flow().active_cell_id
    assert active_cell_id is not None
    return cells().at_position(cells().from_id(active_cell_id).position + offset)


def last_run_cell() -> Optional["Cell"]:
    """Return the most recently executed cell, or ``None`` if none have run."""
    return cells().at_counter(cells().exec_counter() - 1)


def namespaces() -> Type["Namespace"]:
    """Return the :class:`~ipyflow.data_model.namespace.Namespace` class."""
    return _NamespaceContainer[0]


def scopes() -> Type["Scope"]:
    """Return the :class:`~ipyflow.data_model.scope.Scope` class."""
    return _ScopeContainer[0]


if TYPE_CHECKING:

    @overload
    def symbols(sym: None = None) -> Type["Symbol"]:
        ...

    @overload
    def symbols(sym: "Symbol") -> "Symbol":
        ...


def symbols(sym: Optional["Symbol"] = None) -> Union[Type["Symbol"], "Symbol"]:
    """Access the :class:`~ipyflow.data_model.symbol.Symbol` model.

    Called with no argument, returns the ``Symbol`` *class*; called with a
    ``Symbol`` instance, returns it unchanged. The pass-through form is a
    convenience for generic code that accepts either the class or an instance.
    """
    if sym is None:
        return _SymbolContainer[0]
    else:
        return sym


def statements() -> Type["Statement"]:
    """Return the :class:`~ipyflow.data_model.statement.Statement` class."""
    return _StatementContainer[0]


def timestamps() -> Type["Timestamp"]:
    """Return the :class:`~ipyflow.data_model.timestamp.Timestamp` class."""
    return _TimestampContainer[0]
