# -*- coding: utf-8 -*-
import ast
import logging
import textwrap
from dataclasses import dataclass
from types import FrameType
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    cast,
)

import pyccolo as pyc
from IPython import get_ipython

from ipyflow import singletons
from ipyflow.analysis.symbol_ref import SymbolRef
from ipyflow.data_model.code_cell import CodeCell, cells
from ipyflow.data_model.data_symbol import DataSymbol
from ipyflow.data_model.namespace import Namespace
from ipyflow.data_model.scope import Scope
from ipyflow.data_model.timestamp import Timestamp
from ipyflow.frontend import FrontendCheckerResult
from ipyflow.line_magics import make_line_magic
from ipyflow.run_mode import (
    ExecutionMode,
    ExecutionSchedule,
    FlowDirection,
    FlowRunMode,
    Highlights,
)
from ipyflow.tracing.ipyflow_tracer import DataflowTracer
from ipyflow.tracing.watchpoint import Watchpoint
from ipyflow.types import CellId, SupportedIndexType
from ipyflow.utils.misc_utils import cleanup_discard

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class NotebookSafetySettings(NamedTuple):
    test_context: bool
    use_comm: bool
    mark_waiting_symbol_usages_unsafe: bool
    mark_typecheck_failures_unsafe: bool
    mark_phantom_cell_usages_unsafe: bool
    mode: FlowRunMode


@dataclass
class MutableNotebookSafetySettings:
    dataflow_enabled: bool
    trace_messages_enabled: bool
    highlights: Highlights
    static_slicing_enabled: bool
    dynamic_slicing_enabled: bool
    exec_mode: ExecutionMode
    exec_schedule: ExecutionSchedule
    flow_order: FlowDirection
    warn_out_of_order_usages: bool
    lint_out_of_order_usages: bool
    syntax_transforms_enabled: bool
    syntax_transforms_only: bool
    max_external_call_depth_for_tracing: int


class NotebookFlow(singletons.NotebookFlow):
    """Holds all the state necessary to capture dataflow in Jupyter notebooks."""

    def __init__(
        self,
        cell_magic_name=None,
        use_comm=False,
        **kwargs,
    ):
        super().__init__()
        cells().clear()
        self.settings: NotebookSafetySettings = NotebookSafetySettings(
            test_context=kwargs.pop("test_context", False),
            use_comm=use_comm,
            mark_waiting_symbol_usages_unsafe=kwargs.pop(
                "mark_waiting_symbol_usages_unsafe", True
            ),
            mark_typecheck_failures_unsafe=kwargs.pop(
                "mark_typecheck_failures_unsafe", False
            ),
            mark_phantom_cell_usages_unsafe=kwargs.pop(
                "mark_phantom_cell_usages_unsafe", False
            ),
            mode=FlowRunMode.get(),
        )
        self.mut_settings: MutableNotebookSafetySettings = (
            MutableNotebookSafetySettings(
                dataflow_enabled=kwargs.pop("dataflow_enabled", True),
                trace_messages_enabled=kwargs.pop("trace_messages_enabled", False),
                highlights=kwargs.pop("highlights", Highlights.EXECUTED),
                static_slicing_enabled=kwargs.pop("static_slicing_enabled", True),
                dynamic_slicing_enabled=kwargs.pop("dynamic_slicing_enabled", True),
                exec_mode=ExecutionMode(kwargs.pop("exec_mode", ExecutionMode.NORMAL)),
                exec_schedule=ExecutionSchedule(
                    kwargs.pop("exec_schedule", ExecutionSchedule.LIVENESS_BASED)
                ),
                flow_order=FlowDirection(
                    kwargs.pop("flow_direction", FlowDirection.IN_ORDER)
                ),
                warn_out_of_order_usages=kwargs.pop("warn_out_of_order_usages", False),
                lint_out_of_order_usages=kwargs.pop("lint_out_of_order_usages", False),
                syntax_transforms_enabled=kwargs.pop("syntax_transforms_enabled", True),
                syntax_transforms_only=kwargs.pop("syntax_transforms_only", False),
                max_external_call_depth_for_tracing=kwargs.pop(
                    "max_external_call_depth_for_tracing", 3
                ),
            )
        )
        # Note: explicitly adding the types helps PyCharm intellisense
        self.namespaces: Dict[int, Namespace] = {}
        # TODO: wrap this in something that clears the dict entry when the set is 0 length
        self.aliases: Dict[int, Set[DataSymbol]] = {}
        self.dynamic_data_deps: Dict[Timestamp, Set[Timestamp]] = {}
        self.static_data_deps: Dict[Timestamp, Set[Timestamp]] = {}
        self.global_scope: Scope = Scope()
        self.virtual_symbols: Scope = Scope()
        self._virtual_symbols_inited: bool = False
        self.updated_symbols: Set[DataSymbol] = set()
        self.updated_reactive_symbols: Set[DataSymbol] = set()
        self.updated_deep_reactive_symbols: Set[DataSymbol] = set()
        self.active_watchpoints: List[Tuple[Tuple[Watchpoint, ...], DataSymbol]] = []
        self.blocked_reactive_timestamps_by_symbol: Dict[DataSymbol, int] = {}
        self.statement_to_func_cell: Dict[int, DataSymbol] = {}
        self._active_cell_id: Optional[CellId] = None
        self.waiter_usage_detected = False
        self.out_of_order_usage_detected_counter: Optional[int] = None
        if cell_magic_name is None:
            self._cell_magic = None
        else:
            self._cell_magic = singletons.kernel().make_cell_magic(cell_magic_name)
        self._line_magic = make_line_magic(self)
        self._prev_cell_waiting_symbols: Set[DataSymbol] = set()
        self._cell_name_to_cell_num_mapping: Dict[str, int] = {}
        self._exception_raised_during_execution: Optional[Exception] = None
        self._saved_debug_message: Optional[str] = None
        self.min_timestamp = -1
        self.min_cascading_reactive_cell_num = -1
        self._tags: Tuple[str, ...] = ()
        self.last_executed_content: Optional[str] = None
        self.last_executed_cell_id: Optional[CellId] = None
        self._comm_handlers: Dict[
            str, Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]
        ] = {}
        self.register_comm_handler("change_active_cell", self.handle_change_active_cell)
        self.register_comm_handler(
            "compute_exec_schedule", self.handle_compute_exec_schedule
        )
        self.register_comm_handler("reactivity_cleanup", self.handle_reactivity_cleanup)
        self.register_comm_handler("refresh_symbols", self.handle_refresh_symbols)
        self.register_comm_handler("upsert_symbol", self.handle_upsert_symbol)
        self.register_comm_handler(
            "register_dynamic_comm_handler", self.handle_register_dynamic_comm_handler
        )
        self.fs: Namespace = None
        self.display_sym: DataSymbol = None
        if use_comm:
            get_ipython().kernel.comm_manager.register_target(
                __package__, self._comm_target
            )

    def init_virtual_symbols(self) -> None:
        if self._virtual_symbols_inited:
            return
        self.fs = Namespace(Namespace.FILE_SYSTEM, "fs")
        self.display_sym = self.virtual_symbols.upsert_data_symbol_for_name(
            "display", DataSymbol.DISPLAY
        )
        self._virtual_symbols_inited = True

    def initialize(self, *, entrypoint: Optional[str] = None, **kwargs) -> None:
        self.mut_settings.dataflow_enabled = kwargs.get("dataflow_enabled", True)
        self.mut_settings.syntax_transforms_enabled = kwargs.get(
            "syntax_transforms_enabled", False
        )
        self.mut_settings.syntax_transforms_only = kwargs.get(
            "syntax_transforms_only", False
        )
        self.mut_settings.exec_mode = ExecutionMode(
            kwargs.get("exec_mode", ExecutionMode.NORMAL)
        )
        self.mut_settings.exec_schedule = ExecutionSchedule(
            kwargs.get("exec_schedule", ExecutionSchedule.HYBRID_DAG_LIVENESS_BASED)
        )
        self.mut_settings.flow_order = FlowDirection(
            kwargs.get("flow_order", FlowDirection.IN_ORDER)
        )
        self.mut_settings.highlights = Highlights(
            kwargs.get("highlights", Highlights.EXECUTED)
        )
        self.mut_settings.max_external_call_depth_for_tracing = kwargs.get(
            "max_external_call_depth_for_tracing",
            self.mut_settings.max_external_call_depth_for_tracing,
        )

    @property
    def is_develop(self) -> bool:
        return self.settings.mode == FlowRunMode.DEVELOP

    @property
    def is_test(self) -> bool:
        return self.settings.test_context

    @property
    def trace_messages_enabled(self) -> bool:
        return self.mut_settings.trace_messages_enabled

    @trace_messages_enabled.setter
    def trace_messages_enabled(self, new_val) -> None:
        self.mut_settings.trace_messages_enabled = new_val

    def get_first_full_symbol(self, obj_id: int) -> Optional[DataSymbol]:
        for alias in self.aliases.get(obj_id, []):
            if not alias.is_anonymous:
                return alias
        return None

    @staticmethod
    def cell_counter() -> int:
        return cells().exec_counter()

    def add_dynamic_data_dep(
        self, child: Timestamp, parent: Timestamp, sym: DataSymbol
    ) -> None:
        self.dynamic_data_deps.setdefault(child, set()).add(parent)
        cells().from_timestamp(child).add_dynamic_parent(
            cells().from_timestamp(parent), sym
        )

    def add_static_data_dep(
        self, child: Timestamp, parent: Timestamp, sym: DataSymbol
    ) -> None:
        self.static_data_deps.setdefault(child, set()).add(parent)
        cells().from_timestamp(child).add_static_parent(
            cells().from_timestamp(parent), sym
        )

    def reset_cell_counter(self):
        # only called in test context
        assert not singletons.kernel().settings.store_history
        self.dynamic_data_deps.clear()
        self.static_data_deps.clear()
        for sym in self.all_data_symbols():
            sym._timestamp = (
                sym._max_inner_timestamp
            ) = sym.required_timestamp = Timestamp.uninitialized()
            sym.timestamp_by_used_time.clear()
            sym.timestamp_by_liveness_time.clear()
        cells().clear()

    def set_exception_raised_during_execution(
        self, new_val: Optional[Exception] = None
    ) -> Optional[Exception]:
        ret = self._exception_raised_during_execution
        self._exception_raised_during_execution = new_val
        return ret

    def get_position(self, frame: FrameType) -> Tuple[Optional[int], int]:
        try:
            cell_num = self._cell_name_to_cell_num_mapping.get(
                frame.f_code.co_filename, None
            )
            if cell_num is None:
                cell_num = self.cell_counter()
            return cell_num, frame.f_lineno
        except KeyError as e:
            logger.error(
                "key error while retrieving cell for %s", frame.f_code.co_filename
            )
            raise e

    def set_name_to_cell_num_mapping(self, frame: FrameType):
        self._cell_name_to_cell_num_mapping[
            frame.f_code.co_filename
        ] = cells().exec_counter()

    def is_cell_file(self, fname: str) -> bool:
        return fname in self._cell_name_to_cell_num_mapping

    def set_active_cell(self, cell_id: CellId) -> None:
        self._active_cell_id = cell_id

    def set_tags(self, tags: Tuple[str, ...]) -> None:
        self._tags = tags

    def _comm_target(self, comm, open_msg) -> None:
        @comm.on_msg
        def _responder(msg):
            request = msg["content"]["data"]
            self.handle(request, comm=comm)

        self.initialize(**open_msg.get("content", {}).get("data", {}))
        comm.send({"type": "establish"})

    def _create_untracked_cells_for_content(
        self, content_by_cell_id: Dict[CellId, str]
    ):
        for cell_id, content in content_by_cell_id.items():
            cell = cells().from_id(cell_id)
            if cell is not None:
                continue
            cells().create_and_track(cell_id, content, (), bump_cell_counter=False)

    def _recompute_ast_for_dirty_cells(self, content_by_cell_id: Dict[CellId, str]):
        for cell_id, content in content_by_cell_id.items():
            if cell_id == self.last_executed_cell_id:
                continue
            cell = cells().from_id(cell_id)
            if cell is None or cell.current_content == content:
                continue
            prev_content = cell.current_content
            try:
                cell.current_content = content
                cell.to_ast()
            except SyntaxError:
                cell.current_content = prev_content

    def register_comm_handler(
        self,
        msg_type: str,
        handler: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]],
        overwrite: bool = False,
    ) -> None:
        if msg_type in self._comm_handlers and not overwrite:
            raise ValueError("handler already registered for msg type of %s" % msg_type)
        self._comm_handlers[msg_type] = handler

    def handle(self, request: Dict[str, Any], comm=None) -> None:
        request_type = request["type"]
        handler = self._comm_handlers.get(request_type, None)
        if handler is None:
            dbg_msg = "Unsupported request type for request %s" % request
            logger.error(dbg_msg)
            self._saved_debug_message = dbg_msg
            return
        try:
            response = handler(request)
        except Exception as e:
            response = {
                "type": request_type,
                "error": str(e),
            }
        if comm is not None:
            if response is None:
                response = {"type": request_type}
            try:
                comm.send(response)
            except TypeError as e:
                raise Exception(
                    "unable to serialize response for request of type %s" % request_type
                ) from e

    def handle_change_active_cell(self, request) -> Optional[Dict[str, Any]]:
        self.set_active_cell(request["active_cell_id"])
        return None

    def handle_compute_exec_schedule(self, request) -> Optional[Dict[str, Any]]:
        if self._active_cell_id is None:
            self.set_active_cell(request.get("executed_cell_id", None))
        last_cell_id = request.get("executed_cell_id", None)
        cell_metadata_by_id = request.get("cell_metadata_by_id", None)
        cells_to_check = None
        if cell_metadata_by_id is not None:
            cell_metadata_by_id = {
                cell_id: metadata
                for cell_id, metadata in cell_metadata_by_id.items()
                if metadata["type"] == "code"
                or metadata.get("override_live_refs", None)
                or metadata.get("override_dead_refs", None)
            }
            order_index_by_id = {
                cell_id: metadata["index"]
                for cell_id, metadata in cell_metadata_by_id.items()
            }
            content_by_cell_id = {
                cell_id: metadata["content"]
                for cell_id, metadata in cell_metadata_by_id.items()
            }
            override_live_refs_by_cell_id = {
                cell_id: metadata["override_live_refs"]
                for cell_id, metadata in cell_metadata_by_id.items()
                if metadata.get("override_live_refs", None)
            }
            override_dead_refs_by_cell_id = {
                cell_id: metadata["override_dead_refs"]
                for cell_id, metadata in cell_metadata_by_id.items()
                if metadata.get("override_dead_refs", None)
            }
            self._create_untracked_cells_for_content(content_by_cell_id)
            cells().set_cell_positions(order_index_by_id)
            cells().set_override_refs(
                override_live_refs_by_cell_id, override_dead_refs_by_cell_id
            )
            cells_to_check = (
                cell
                for cell in (cells().from_id(cell_id) for cell_id in order_index_by_id)
                if cell is not None
            )
            self._recompute_ast_for_dirty_cells(content_by_cell_id)
        response = self.check_and_link_multiple_cells(
            cells_to_check=cells_to_check, last_executed_cell_id=last_cell_id
        ).to_json()
        response["type"] = "compute_exec_schedule"
        response["exec_mode"] = self.mut_settings.exec_mode.value
        response["exec_schedule"] = self.mut_settings.exec_schedule.value
        response["flow_order"] = self.mut_settings.flow_order.value
        response["last_executed_cell_id"] = last_cell_id
        response["highlights"] = self.mut_settings.highlights.value
        return response

    def handle_reactivity_cleanup(self, _request=None) -> Optional[Dict[str, Any]]:
        for cell in cells().all_cells_most_recently_run_for_each_id():
            cell.set_ready(False)
        self.min_cascading_reactive_cell_num = self.cell_counter()
        return None

    def handle_refresh_symbols(self, request) -> Optional[Dict[str, Any]]:
        for symbol_str in request.get("symbols", []):
            symbol_ref = SymbolRef.from_string(symbol_str)
            for resolved in symbol_ref.gen_resolved_symbols(
                self.global_scope, only_yield_final_symbol=True
            ):
                resolved.dsym.refresh()
        return None

    def handle_upsert_symbol(self, request) -> Optional[Dict[str, Any]]:
        symbol_name = request["symbol"]
        user_globals = get_ipython().user_global_ns
        if symbol_name not in user_globals:
            return None
        dep_symbols = set()
        for dep in request.get("deps", []):
            dep_sym = SymbolRef.resolve(dep)
            if dep_sym is not None:
                dep_symbols.add(dep_sym)
        obj = user_globals.get(symbol_name)
        prev_sym = self.global_scope.lookup_data_symbol_by_name_this_indentation(
            symbol_name
        )
        if prev_sym is not None and prev_sym.obj is obj:
            return None
        with Timestamp.offset(stmt_offset=-1):
            self.global_scope.upsert_data_symbol_for_name(
                symbol_name, obj, dep_symbols, ast.parse("pass").body[0]
            )
        return None

    def handle_register_dynamic_comm_handler(self, request) -> Optional[Dict[str, Any]]:
        handler_msg_type = request.get("msg_type", None)
        handler_str = request.get("handler", None)
        if handler_msg_type is None or handler_str is None:
            return None
        handler_str = handler_str.strip()
        handler_str = textwrap.indent(textwrap.dedent(handler_str).strip(), " " * 4)
        handler_fun_name = f"_X5ix_{handler_msg_type}_handler"
        handler_str = f"def {handler_fun_name}(self, request):\n{handler_str}"
        exec(handler_str, globals())
        handler = globals().pop(handler_fun_name, None)
        self.register_comm_handler(
            handler_msg_type,
            lambda request_: handler(self, request_),
            overwrite=request.get("overwrite", False),
        )
        return None

    def check_and_link_multiple_cells(
        self,
        cells_to_check: Optional[Iterable[CodeCell]] = None,
        update_liveness_time_versions: bool = False,
        last_executed_cell_id: Optional[CellId] = None,
    ) -> FrontendCheckerResult:
        result = FrontendCheckerResult.empty()
        if (
            DataflowTracer not in singletons.kernel().registered_tracers
            or not DataflowTracer.initialized()
        ):
            return result
        return result.compute_frontend_checker_result(
            cells_to_check=cells_to_check,
            update_liveness_time_versions=update_liveness_time_versions,
            last_executed_cell_id=last_executed_cell_id,
        )

    def _safety_precheck_cell(self, cell: CodeCell) -> None:
        for tracer in singletons.kernel().registered_tracers:
            # just make sure all tracers are initialized
            tracer.instance()
        checker_result = self.check_and_link_multiple_cells(
            cells_to_check=[cell],
            update_liveness_time_versions=self.mut_settings.static_slicing_enabled,
        )
        if cell.cell_id in checker_result.waiting_cells:
            self.waiter_usage_detected = True
        unsafe_order_cells = checker_result.unsafe_order_cells.get(cell.cell_id, None)
        if unsafe_order_cells is not None:
            self.out_of_order_usage_detected_counter = max(
                (cell.position, cell.cell_ctr) for cell in unsafe_order_cells
            )[1]

    def _resync_symbols(self, symbols: Iterable[DataSymbol]):
        for dsym in symbols:
            if not dsym.containing_scope.is_global:
                continue
            try:
                obj = get_ipython().user_global_ns.get(dsym.name, None)
                if obj is None:
                    continue
            except:  # noqa
                # cinder runtime can throw an exception here due to lazy imports that fail
                continue
            if dsym.obj_id == id(obj):
                continue
            for alias in self.aliases.get(dsym.cached_obj_id, set()) | self.aliases.get(
                dsym.obj_id, set()
            ):
                containing_namespace = alias.containing_namespace
                if containing_namespace is None:
                    continue
                containing_obj = containing_namespace.obj
                if containing_obj is None:
                    continue
                # TODO: handle dict case too
                if isinstance(containing_obj, list) and containing_obj[-1] is obj:
                    containing_namespace._subscript_data_symbol_by_name.pop(
                        alias.name, None
                    )
                    alias.name = len(containing_obj) - 1
                    alias.update_obj_ref(obj)
                    containing_namespace._subscript_data_symbol_by_name[
                        alias.name
                    ] = alias
            cleanup_discard(self.aliases, dsym.cached_obj_id, dsym)
            cleanup_discard(self.aliases, dsym.obj_id, dsym)
            self.aliases.setdefault(id(obj), set()).add(dsym)
            dsym.update_obj_ref(obj)

    @property
    def cell_magic_name(self):
        return self._cell_magic.__name__

    @property
    def line_magic_name(self):
        return self._line_magic.__name__

    def all_data_symbols(self) -> Iterable[DataSymbol]:
        for alias_set in self.aliases.values():
            yield from alias_set

    def test_and_clear_waiter_usage_detected(self):
        ret = self.waiter_usage_detected
        self.waiter_usage_detected = False
        return ret

    def test_and_clear_out_of_order_usage_detected_counter(self):
        ret = self.out_of_order_usage_detected_counter
        self.out_of_order_usage_detected_counter = None
        return ret

    def gc(self):
        # Need to do the garbage check and the collection separately
        garbage_syms = [
            dsym for dsym in self.all_data_symbols() if dsym.is_new_garbage()
        ]
        for dsym in garbage_syms:
            dsym.collect_self_garbage()

    def retrieve_namespace_attr_or_sub(
        self, obj: Any, attr_or_sub: SupportedIndexType, is_subscript: bool
    ):
        try:
            with pyc.allow_reentrant_event_handling():
                if is_subscript:
                    # TODO: more complete list of things that are checkable
                    #  or could cause side effects upon subscripting
                    return obj[attr_or_sub]
                else:
                    if self.is_develop:
                        assert isinstance(attr_or_sub, str)
                    return getattr(obj, cast(str, attr_or_sub))
        except (AttributeError, IndexError, KeyError):
            raise
        except Exception as e:
            if self.is_develop:
                logger.warning("unexpected exception: %s", e)
                logger.warning("object: %s", obj)
                logger.warning("attr / subscript: %s", attr_or_sub)
            raise e
