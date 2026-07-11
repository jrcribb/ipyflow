Introspecting the dataflow graph
================================

Everything ipyflow shows in the UI is backed by a dataflow graph you can query
directly from Python. This guide is a task-oriented tour of the ``ipyflow.api``
helpers; the per-function signatures are in :doc:`../reference/api`.

The helpers all take the *value* of a notebook symbol and, thanks to a tracer
hook that intercepts the call argument, resolve it to the corresponding graph
node. So you write ``deps(y)``, not ``deps("y")``.

Lifting a value to its Symbol
-----------------------------

``lift`` returns the internal :class:`~ipyflow.data_model.symbol.Symbol` for a
value. It is the foundation the other helpers build on, and useful when you want
to read a symbol's attributes directly:

.. testcode::

   run_cell("x = y = 42")
   run_cell("assert lift(x).readable_name == 'x'")
   run_cell("assert lift(y).readable_name == 'y'")

``lift`` raises ``ValueError`` if the value cannot be resolved to a tracked
symbol, so it doubles as an assertion that a value *is* graph-tracked.

Dependencies and dependents
---------------------------

``deps`` and ``users`` give the immediate neighbors; ``rdeps`` and ``rusers``
give the transitive closures. All four skip anonymous internal symbols and return
plain lists of ``Symbol`` objects:

.. testcode::

   run_cell("a = 0")
   run_cell("b = a + 0")
   run_cell("c = b + 0")

   run_cell("assert deps(b) == [lift(a)]")
   run_cell("assert users(a) == [lift(b)]")

   run_cell("assert set(rdeps(c)) == {lift(a), lift(b)}")
   run_cell("assert set(rusers(a)) == {lift(b), lift(c)}")

Dependencies work below the variable level too. A value assembled from several
sources reports each contributing symbol:

.. testcode::

   run_cell('''
       def f():
           p = 0
           q = 1
           return p + q
   ''')
   run_cell("z = f()")
   run_cell("assert sorted(repr(d) for d in deps(z)) == ['<f>', '<p>', '<q>']")

Note the ``<name>`` repr that ipyflow uses for symbols -- it is what appears in
``%flow`` output and is convenient for order-independent assertions.

Reconstructing code
-------------------

``code`` returns the backward program slice for a symbol: the minimal sequence of
cells needed to recompute it. ``timestamp`` returns the
:class:`~ipyflow.data_model.timestamp.Timestamp` of its last update.

.. testcode::

   run_cell = reset_flow()  # start this example from a clean notebook
   run_cell("first = 0")
   run_cell("second = first + 1")
   run_cell("assert str(code(second)) == '# Cell 1\\nfirst = 0\\n\\n# Cell 2\\nsecond = first + 1'")
   run_cell("assert timestamp(second).cell_num == 2")

The reconstructed code is executable: feeding it back through ``pyc.exec``
reproduces the original values, which is a handy way to verify a slice.

.. testcode::

   run_cell("env = pyc.exec(str(code(second)))")
   run_cell("assert env['first'] == 0 and env['second'] == 1")

Tags
----

Tags are free-form string labels you attach to symbols, useful for grouping
related values or driving custom tooling. Use ``set_tag``, ``unset_tag``, and
``has_tag``:

.. testcode::

   run_cell("total = 0")
   run_cell("assert not has_tag(total, 'checkpoint')")
   run_cell("set_tag(total, 'checkpoint')")
   run_cell("assert has_tag(total, 'checkpoint')")
   run_cell("unset_tag(total, 'checkpoint')")
   run_cell("assert not has_tag(total, 'checkpoint')")

Cells can be tagged too, via ``%flow tag`` / ``%flow show_tags`` -- see
:doc:`../reference/flow_magic`.

Watchpoints
-----------

A watchpoint fires a callback whenever a symbol is written. ``watchpoints``
returns the symbol's :class:`~ipyflow.tracing.watchpoint.Watchpoints` collection;
register a predicate with ``.add``:

.. testcode::

   run_cell("counter = 0")
   run_cell("watchpoints(counter).add(lambda obj, position, name: None)")
   run_cell("assert len(watchpoints(counter)) == 1")

The predicate is called with ``(obj, position, symbol_name)`` on each update;
returning a truthy value signals the watchpoint condition was met.

Forcing a mutation
------------------

Sometimes ipyflow cannot see that an in-place operation changed an object (for
example, mutation hidden inside third-party C code). ``mutate`` bumps a symbol's
timestamp so downstream cells treat it as freshly updated:

.. testcode::

   run_cell("data = []")
   run_cell("before = timestamp(data).cell_num")
   run_cell("mutate(data)")
   run_cell("assert timestamp(data).cell_num > before")

Recovering prior cell output
----------------------------

Because ipyflow captures each cell's output, it can recover input and output from
earlier executions -- valuable when autosave has overwritten a result you wanted.
``stdout`` and ``stderr`` return captured streams by cell number, and
``reproduce_cell`` re-renders a past execution:

.. testcode::

   run_cell = reset_flow()  # start this example from a clean notebook
   run_cell("print('captured output')")
   run_cell("assert stdout(1) is not None and 'captured output' in stdout(1)")

.. testoutput::

   captured output

``reproduce_cell(ctr, show_input=True, show_output=True, lookback=0)`` reproduces
cell ``ctr``; ``lookback=1`` reaches the *previous* execution of that cell, which
is how you recover a result an autosaved reactive re-run replaced:

.. code-block:: python

   from ipyflow import reproduce_cell
   reproduce_cell(4, lookback=1)  # the execution of cell 4 before the latest one
