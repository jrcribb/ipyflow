Your first reactive notebook
============================

This page builds a small notebook and inspects the dataflow graph ipyflow
constructs as the cells run. The narrative uses ``run_cell("...")`` to stand in
for executing a notebook cell so that every claim here is checked when the docs
are built; in JupyterLab you would type the same code into cells.

.. note::

   The dataflow helpers used below (``deps``, ``users``, ``lift``, ``code``,
   ``timestamp``, ...) live in the top-level ``ipyflow`` package. In a real
   session, run ``from ipyflow import deps, users, lift, code, timestamp`` once
   at the top of your notebook. Throughout this documentation those names are
   assumed to already be in scope.

   Two names in these examples are documentation helpers, not part of ipyflow's
   API: ``run_cell("...")`` executes its argument as a notebook cell, and
   ``reset_flow()`` (seen in later pages) starts a fresh kernel so an example can
   number its cells from 1. In JupyterLab you simply type into cells and restart
   the kernel instead.

Defining some cells
-------------------

Start with a couple of ordinary assignments. ipyflow watches each assignment and
usage and records an edge whenever one symbol is computed from another.

.. testcode::

   run_cell("raw = 10")
   run_cell("scaled = raw * 2")
   run_cell("summary = scaled + 1")

Nothing about the code changed -- ``raw``, ``scaled``, and ``summary`` are plain
Python variables. What ipyflow adds is a *graph* connecting them.

Who depends on whom
-------------------

``deps`` returns the immediate upstream dependencies of a symbol, and ``users``
returns its immediate downstream dependents:

.. testcode::

   run_cell("assert deps(summary) == [lift(scaled)]")
   run_cell("assert deps(scaled) == [lift(raw)]")
   run_cell("assert users(raw) == [lift(scaled)]")

Passing the *value* of a symbol (``scaled``) to these helpers works because
ipyflow's tracer intercepts the argument and substitutes the corresponding graph
node. ``lift`` performs that same value-to-node lookup explicitly, returning the
internal :class:`~ipyflow.data_model.symbol.Symbol` -- which is what ``deps`` and
``users`` compare against and return.

To follow the graph transitively rather than one hop at a time, use ``rdeps``
(recursive dependencies) and ``rusers`` (recursive dependents):

.. testcode::

   run_cell("assert set(rdeps(summary)) == {lift(raw), lift(scaled)}")
   run_cell("assert set(rusers(raw)) == {lift(scaled), lift(summary)}")

Reconstructing a value
----------------------

Because ipyflow knows the full provenance of a symbol, it can reconstruct the
minimal sequence of code that produces it -- a *backward program slice*. The
``code`` helper returns that slice:

.. testcode::

   run_cell("print(code(summary))")

.. testoutput::

   # Cell 1
   raw = 10

   # Cell 2
   scaled = raw * 2

   # Cell 3
   summary = scaled + 1

The slice includes only the cells that ``summary`` actually depends on. Had there
been unrelated cells in between, they would be omitted. The same slice is
available per cell via ``cells(n).slice()`` (see :doc:`../concepts/slicing`).

When was a symbol last updated
------------------------------

Every symbol carries a :class:`~ipyflow.data_model.timestamp.Timestamp` recording
the ``(cell_num, stmt_num)`` at which it was last written. ``cell_num`` is the
1-indexed execution counter; ``stmt_num`` is the 0-indexed statement within that
cell:

.. testcode::

   run_cell("assert timestamp(raw).cell_num == 1")
   run_cell("assert timestamp(summary).cell_num == 3")
   run_cell("assert repr(timestamp(summary)) == 'Timestamp(cell_num=3, stmt_num=0)'")

Now re-run the first cell with a new value. ipyflow stamps ``raw`` with a fresh,
later timestamp and -- crucially -- marks everything downstream as out of date:

.. testcode::

   run_cell("raw = 99")
   # `raw` was just rewritten, so its timestamp is now newer than `summary`'s.
   run_cell("assert timestamp(raw).cell_num > timestamp(summary).cell_num")
   # `scaled` and `summary` still hold their old values but now have a newer
   # upstream dependency, so ipyflow considers them stale/waiting.
   run_cell("assert lift(scaled).is_waiting")

What reactive execution adds
----------------------------

In the plain-API view above, ipyflow *detected* that ``scaled`` and ``summary``
went stale but did not act on it -- that is the default **lazy** execution mode,
which only runs the cell you execute. In JupyterLab, the extension surfaces this
staleness visually (orange/purple dependency dots) and, when you opt into
**reactive** mode, automatically re-executes the stale downstream cells so the
notebook always reflects a top-to-bottom run.

The next guide, :doc:`../guides/reactive_execution`, covers the execution modes,
flow direction, and scheduling that govern this behavior. To go deeper on the API
used above, see :doc:`../guides/introspection_api`.
