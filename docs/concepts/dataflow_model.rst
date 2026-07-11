The dataflow model
==================

ipyflow's features -- staleness detection, reactive scheduling, slicing,
memoization -- all read from a single in-memory structure: a **dataflow graph**
whose nodes are symbols and whose edges are the dependencies between them. This
page describes the objects that make up that model. Their programmatic surface is
cataloged in :doc:`../reference/data_model`.

ipyflow builds the graph by using `pyccolo <https://pyccolo.readthedocs.io>`_ to
instrument executing code: the AST of each cell is rewritten to insert tracing
hooks, and as the code runs those hooks observe every assignment, usage, and
mutation. Nothing about your code changes -- the instrumentation is transparent.

Timestamp
---------

A :class:`~ipyflow.data_model.timestamp.Timestamp` is a ``(cell_num, stmt_num)``
pair naming a single point in execution:

- ``cell_num`` -- the cell execution counter, which increments every time *any*
  cell runs (so it strictly increases across the session).
- ``stmt_num`` -- the 0-indexed statement within that cell execution.

Timestamps are how ipyflow reasons about "before" and "after". A symbol is
**stale** when one of its dependencies carries a newer timestamp than the symbol
itself -- that comparison is the heart of staleness detection.

.. cell::
   :reset:

   a = 1

.. cell::

   b = a + 1

.. cell::

   print(timestamp(a), timestamp(b))

.. cell-output::

   Timestamp(cell_num=1, stmt_num=0) Timestamp(cell_num=2, stmt_num=0)

Re-running the first cell gives ``a`` a newer timestamp than ``b``, so ``b`` is
now stale -- which is exactly what ipyflow flags in the UI:

.. cell::

   a = 2

.. cell::

   print(lift(b).is_waiting)

.. cell-output::

   True

Symbol
------

A :class:`~ipyflow.data_model.symbol.Symbol` is a node in the graph -- a variable
binding (or an attribute/subscript member). Each symbol tracks:

- its **name** (``readable_name``) and a reference to the actual Python **obj**;
- its **timestamp**, the point at which it was last written;
- its **parents** -- the symbols it was computed from (incoming edges);
- its **children** -- the symbols computed from it (outgoing edges);
- the **scope** that contains it.

``parents`` and ``children`` are exactly what the ``deps`` / ``users`` helpers
expose, filtered to user-visible symbols. Following them transitively yields the
backward and forward slices.

An important subtlety is **aliasing**: several symbols can bind the *same* object.
ipyflow indexes symbols by object id (``aliases: obj_id -> {Symbol}``) so that a
mutation to an object is attributed to every name pointing at it.

Scope and Namespace
-------------------

A :class:`~ipyflow.data_model.scope.Scope` is a symbol table mapping names to
symbols. Scopes nest the way Python's do:

- the **global scope** holds top-level notebook variables;
- a **function scope** holds a function's locals;
- a **namespace scope** holds an object's attributes or items.

That last kind is a :class:`~ipyflow.data_model.namespace.Namespace` -- a scope
attached to a particular object (keyed by ``obj_id``) that represents members like
``df.columns``, ``config["key"]``, or ``obj.attr``. Namespaces are created lazily,
the first time a member is accessed, and they are what let ipyflow track
dependencies *below* the variable level: a cell that reads ``x[0]`` depends on the
``x[0]`` member symbol, not on all of ``x``, so an unrelated change to ``x[1]``
does not make it stale.

Cell and Statement
------------------

A :class:`~ipyflow.data_model.cell.Cell` represents a notebook code cell. It
records the frontend ``cell_id``, the execution counter ``cell_ctr`` at which it
ran, its ``content``, its ``position`` in the notebook (used for in-order
scheduling), and its edges to other cells -- derived from the symbol edges above.
Cells are the unit the UI and reactive scheduler operate on.

A :class:`~ipyflow.data_model.statement.Statement` is the finer-grained analog:
one AST statement, with its own timestamp and symbol-derived edges. Statement-level
edges are what make *statement* slicing (``%flow slice --stmt``) more precise than
cell slicing.

Putting it together
-------------------

When a cell runs, the tracer creates or updates a ``Symbol`` for each assignment
and records an edge for each usage, stamping everything with the current
``Timestamp``. The central :class:`~ipyflow.flow.NotebookFlow` singleton owns this
state -- the scopes, the alias index, the namespaces, and the per-session settings
-- and answers the questions the frontend and the public API ask of it: *what is
stale?*, *what must re-run?*, *what code reproduces this value?*

The last of those -- turning the graph into runnable code -- is **program
slicing**, covered next in :doc:`slicing`.
