# -*- coding: utf-8 -*-
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Generator, List

from ipyflow.slicing.context import SlicingContext, iter_slicing_contexts


class EnumWithDefault(Enum):
    @classmethod
    def _missing_(cls, value):
        return cls(cls.__default__)  # type: ignore


class ExecutionMode(EnumWithDefault):
    """Whether executing a cell also re-runs its stale dependencies.

    Set with ``%flow mode``. ``LAZY`` is the default and matches stock
    ``ipykernel`` (only the executed cell runs); ``REACTIVE`` additionally re-runs
    stale upstream and downstream cells in dependency order.
    """

    LAZY = __default__ = "lazy"  # type: ignore
    REACTIVE = "reactive"


class ExecutionSchedule(EnumWithDefault):
    """How the set of cells to (re-)run is computed.

    Set with ``%flow schedule``. ``DAG_BASED`` (the default) uses the dynamic
    dataflow graph; ``LIVENESS_BASED`` uses static liveness analysis of cell
    source; ``HYBRID_DAG_LIVENESS_BASED`` combines both and is required for
    incremental reactivity.
    """

    LIVENESS_BASED = "liveness_based"
    DAG_BASED = __default__ = "dag_based"  # type: ignore
    HYBRID_DAG_LIVENESS_BASED = "hybrid_dag_liveness_based"


class FlowDirection(EnumWithDefault):
    """Which dependency edges may drive reactive execution.

    Set with ``%flow direction``. ``IN_ORDER`` (the default) only lets a cell
    trigger cells that appear after it in the notebook; ``ANY_ORDER`` ignores
    spatial position.
    """

    ANY_ORDER = "any_order"
    IN_ORDER = __default__ = "in_order"  # type: ignore


class Highlights(EnumWithDefault):
    """Which cells the frontend visually highlights.

    Set with ``%flow hls`` / ``%flow nohls``. ``EXECUTED`` (the default)
    highlights cells that ran; ``REACTIVE`` highlights reactive updates; ``ALL``
    and ``NONE`` show everything or nothing.
    """

    ALL = "all"
    NONE = "none"
    EXECUTED = __default__ = "executed"  # type: ignore
    REACTIVE = "reactive"


class ReactivityMode(EnumWithDefault):
    """Whether reactive updates are applied all at once or one cell at a time.

    Set with ``%flow reactivity``. ``BATCH`` (the default) recomputes the whole
    affected set together; ``INCREMENTAL`` applies updates one step at a time and
    requires a liveness-aware :class:`ExecutionSchedule`.
    """

    BATCH = __default__ = "batch"  # type: ignore
    INCREMENTAL = "incremental"


# TODO: figure out how to represent different versions of
#  same interface (e.g. jupyterlab 4.0, notebook v7, etc)
class Interface(EnumWithDefault):
    BENTO = "bento"  # ~TODO
    COLAB = "colab"  # TODO
    DATABRICKS = "databricks"  # TODO
    DATALORE = "datalore"  # TODO
    DEEPNOTE = "deepnote"  # TODO
    HEX = "hex"  # TODO
    IPYTHON = "ipython"
    JUPYTER = "jupyter"
    JUPYTERLAB = "jupyterlab"
    NOTEABLE = "noteable"  # TODO
    VSCODE = "vscode"  # TODO
    UNKNOWN = __default__ = "unknown"  # type: ignore


class ColorScheme(EnumWithDefault):
    NORMAL = __default__ = "normal"  # type: ignore
    CLASSIC = "classic"  # type: ignore


class JsonSerializableMixin:
    def to_json(self: Any) -> Dict[str, Any]:
        json = {}
        for key, value in asdict(self).items():
            if isinstance(value, Enum):
                value = value.value
            if not isinstance(value, (bool, float, str)):
                value = str(value)
            json[key] = value
        return json


@dataclass(frozen=True)
class DataflowSettings(JsonSerializableMixin):
    test_context: bool
    mark_waiting_symbol_usages_unsafe: bool
    mark_typecheck_failures_unsafe: bool
    mark_phantom_cell_usages_unsafe: bool


@dataclass
class MutableDataflowSettings(JsonSerializableMixin):
    dataflow_enabled: bool
    trace_messages_enabled: bool
    highlights: Highlights
    interface: Interface
    static_slicing_enabled: bool
    dynamic_slicing_enabled: bool
    exec_mode: ExecutionMode
    exec_schedule: ExecutionSchedule
    flow_order: FlowDirection
    reactivity_mode: ReactivityMode
    push_reactive_updates: bool
    push_reactive_updates_to_cousins: bool
    pull_reactive_updates: bool
    color_scheme: ColorScheme
    warn_out_of_order_usages: bool
    lint_out_of_order_usages: bool
    syntax_transforms_enabled: bool
    syntax_transforms_only: bool
    max_external_call_depth_for_tracing: int
    is_dev_mode: bool

    def slicing_contexts(self) -> List[SlicingContext]:
        """Return the currently-enabled slicing contexts (dynamic and/or static)."""
        ret: List[SlicingContext] = []
        if self.dynamic_slicing_enabled:
            ret.append(SlicingContext.DYNAMIC)
        if self.static_slicing_enabled:
            ret.append(SlicingContext.STATIC)
        return ret

    def iter_slicing_contexts(self) -> Generator[None, None, None]:
        for _ in iter_slicing_contexts(*self.slicing_contexts()):
            yield
