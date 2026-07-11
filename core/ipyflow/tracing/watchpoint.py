# -*- coding: utf-8 -*-
from typing import Any, Callable, Optional, Tuple


class Watchpoint:
    """A single named predicate evaluated whenever a watched symbol is written.

    The predicate is called as ``pred(obj, position=(cell_num, stmt_num),
    symbol_name=...)`` and should return a truthy value when the watchpoint
    condition is met. A ``None`` predicate always passes.
    """

    def __init__(
        self, name: Optional[str], pred: Optional[Callable[..., bool]]
    ) -> None:
        self.name = name
        self.pred = pred

    def __call__(
        self, obj: Any, *, position: Tuple[int, int], symbol_name: str
    ) -> bool:
        return (
            True
            if self.pred is None
            else self.pred(obj, position=position, symbol_name=symbol_name)
        )

    def __repr__(self):
        name_str = (
            "<anonymous-watchpoint>"
            if self.name is None
            else f"<watchpoint-{self.name}>"
        )
        pred_str = (
            "no predicate" if self.pred is None else "predicate " + repr(self.pred)
        )
        return f"{name_str} ({pred_str})"


class Watchpoints(list):
    """The collection of :class:`Watchpoint` objects registered on a symbol.

    Obtain one with ``watchpoints(sym)``. It behaves like a read-only list; add
    watchpoints with :meth:`add` rather than the usual list-mutation methods
    (which are disabled).
    """

    def append(self, *args, **kwargs) -> None:
        raise NotImplementedError("please use the `add` method instead")

    def extend(self, *args, **kwargs) -> None:
        raise NotImplementedError("please use the `add` method instead")

    def __add__(self, *args, **kwargs) -> "Watchpoints":
        raise NotImplementedError("please use the `add` method instead")

    def __iadd__(self, *args, **kwargs) -> "Watchpoints":
        raise NotImplementedError("please use the `add` method instead")

    def __radd__(self, *args, **kwargs) -> "Watchpoints":
        raise NotImplementedError("please use the `add` method instead")

    def add(
        self, pred: Optional[Callable[..., bool]] = None, name: Optional[str] = None
    ):
        """Register a watchpoint.

        :param pred: a callable invoked as ``pred(obj, position=(cell_num,
            stmt_num), symbol_name=...)`` on each write to the watched symbol,
            returning truthy when the condition is met. ``None`` always passes.
        :param name: an optional label for the watchpoint (used in ``repr``).
        """
        super().append(Watchpoint(name, pred))

    def passing(
        self, obj: Any, *, position: Tuple[int, int], symbol_name: str
    ) -> Tuple[Watchpoint, ...]:
        passing_watchpoints = []
        for wp in self:
            if wp(obj, position=position, symbol_name=symbol_name):
                passing_watchpoints.append(wp)
        return tuple(passing_watchpoints)

    def __call__(
        self, obj: Any, *, position: Tuple[int, int], symbol_name: str
    ) -> Tuple[Watchpoint, ...]:
        return self.passing(obj, position=position, symbol_name=symbol_name)
