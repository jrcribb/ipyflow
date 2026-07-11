Data model
==========

These are the classes that make up ipyflow's dataflow graph. The
:doc:`../concepts/dataflow_model` page explains how they fit together; this page
is the class reference. They are internal-heavy -- only the user-facing members
are documented here.

Timestamp
---------

.. autoclass:: ipyflow.data_model.timestamp.Timestamp
   :members: cell_num, stmt_num, current, is_initialized

Symbol
------

Obtain a ``Symbol`` from a value with ``lift(value)``, or from the graph via the
``deps`` / ``users`` helpers.

.. autoclass:: ipyflow.data_model.symbol.Symbol
   :members: readable_name, timestamp, code, is_waiting, is_anonymous,
             add_tag, remove_tag, has_tag

In addition to the documented members above, a ``Symbol`` exposes ``obj`` (the
underlying object), ``parents`` and ``children`` (the dataflow edges, as dicts
keyed by ``Symbol``), and ``containing_scope``.

Cell
----

Access cells with ``cells()`` (the class) and ``cells(id)`` (an instance); see
:doc:`models`.

.. autoclass:: ipyflow.data_model.cell.Cell
   :members: slice, code, reproduce, is_memoized

Instances also carry the attributes set at execution time: ``cell_id`` (frontend
id), ``cell_ctr`` (execution counter), ``current_content`` / ``executed_content``
(source), ``position`` (notebook order), and ``tags``.

Scope, Namespace, and Statement
-------------------------------

A :class:`~ipyflow.data_model.scope.Scope` is a symbol table mapping names to
symbols. A :class:`~ipyflow.data_model.namespace.Namespace` is a ``Scope``
attached to a particular object, representing its attributes and items (for
example ``df.columns`` or ``d["key"]``); this is what enables dependency tracking
below the variable level. A :class:`~ipyflow.data_model.statement.Statement` is
the per-AST-statement analog of a ``Cell`` and underpins statement-level slicing.

These classes are primarily internal; interact with them through the accessors in
:doc:`models` (``scopes()``, ``namespaces()``, ``statements()``) and the concepts
overview in :doc:`../concepts/dataflow_model`.

Watchpoints
-----------

.. autoclass:: ipyflow.tracing.watchpoint.Watchpoints
   :members: add

.. autoclass:: ipyflow.tracing.watchpoint.Watchpoint
