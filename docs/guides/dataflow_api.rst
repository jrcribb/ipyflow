The dataflow API
================

Everything ipyflow shows in the UI is backed by a dataflow graph you can query
from Python. This guide is a tour of the helpers in ``ipyflow.api``, all
re-exported from the top level:

.. code-block:: python

   from ipyflow import deps, users, rdeps, rusers, code, timestamp, lift

Each of these takes the *value* of a notebook symbol; a tracer hook resolves it to
the corresponding graph node, so you write ``deps(y)``, not ``deps("y")``.

Dependencies and dependents
---------------------------

Say two cells compute values from one another:

.. cell::
   :reset:

   x = 0

.. cell::

   y = x + 1

``deps`` gives a symbol's immediate upstream dependencies, ``users`` its immediate
downstream dependents. Symbols print as ``<name>``:

.. cell::

   print(deps(y))

.. cell-output::

   [<x>]

.. cell::

   print(users(x))

.. cell-output::

   [<y>]

``rdeps`` and ``rusers`` follow those edges transitively. With a longer chain:

.. cell::
   :reset:

   a = 0

.. cell::

   b = a + 0

.. cell::

   c = b + 0

.. cell::

   print(sorted(s.readable_name for s in rusers(a)))

.. cell-output::

   ['b', 'c']

Dependencies are tracked below the variable level, too. A value assembled from
several sources reports each contributing symbol:

.. cell::
   :reset:

   def f():
       p = 0
       q = 1
       return p + q

.. cell::

   z = f()

.. cell::

   print(sorted(repr(d) for d in deps(z)))

.. cell-output::

   ['<f>', '<p>', '<q>']

Reconstructing code
-------------------

``code`` returns the backward slice for a symbol -- the minimal sequence of cells
that recomputes it -- and ``timestamp`` reports when it was last updated as a
``(cell_num, stmt_num)`` pair:

.. cell::
   :reset:

   first = 0

.. cell::

   second = first + 1

.. cell::

   print(code(second))

.. cell-output::

   # Cell 1
   first = 0

   # Cell 2
   second = first + 1

.. cell::

   print(timestamp(second))

.. cell-output::

   Timestamp(cell_num=2, stmt_num=0)

The reconstructed code is executable, which makes it easy to check a slice --
feeding it back through ``pyc.exec`` reproduces the original values:

.. cell::

   env = pyc.exec(str(code(second)))
   assert env["first"] == 0 and env["second"] == 1

Lifting a value to its Symbol
-----------------------------

``lift`` returns the internal :class:`~ipyflow.data_model.symbol.Symbol` behind a
value, which the other helpers build on. Reach for it when you want a symbol's
attributes directly:

.. cell::
   :reset:

   total = 41

.. cell::

   print(lift(total).readable_name, "at", lift(total).timestamp)

.. cell-output::

   total at Timestamp(cell_num=1, stmt_num=0)

``lift`` raises ``ValueError`` if the value isn't a tracked symbol, so it doubles
as a check that a value *is* in the graph.

Tags
----

Tags are free-form string labels you attach to symbols -- handy for grouping
related values or driving your own tooling:

.. cell::
   :reset:

   result = 100

.. cell::

   set_tag(result, "checkpoint")
   print(has_tag(result, "checkpoint"))

.. cell-output::

   True

Remove one with ``unset_tag(result, "checkpoint")``. Cells can be tagged too, via
``%flow tag`` -- see :doc:`../reference/flow_magic`.

Watchpoints
-----------

A watchpoint runs a callback whenever a symbol is written. ``watchpoints`` returns
the symbol's :class:`~ipyflow.tracing.watchpoint.Watchpoints` collection; register
a predicate with ``.add``:

.. cell::
   :reset:

   counter = 0

.. cell::

   watchpoints(counter).add(lambda obj, position, name: obj > 100)

The predicate is called as ``pred(obj, position, symbol_name)`` on each update and
signals its condition by returning a truthy value.

Forcing a mutation
------------------

When ipyflow can't see that an in-place operation changed an object -- say a
mutation buried in third-party C code -- ``mutate`` bumps the symbol's timestamp
so downstream cells treat it as freshly updated:

.. cell::
   :reset:

   data = []

.. cell::

   before = timestamp(data).cell_num
   mutate(data)
   assert timestamp(data).cell_num > before

Recovering cell output
----------------------

ipyflow captures each cell's output, so you can recover it later -- useful when a
reactive re-run has overwritten a result. ``stdout`` and ``stderr`` return
captured streams by cell number:

.. cell::
   :reset:

   print("hello from cell 1")

.. cell-output::

   hello from cell 1

Later -- even after autosave has cleared the visible output -- ``stdout`` returns
that captured text (including its trailing newline) by cell number:

.. cell::

   assert stdout(1) == "hello from cell 1\n"

And :func:`~ipyflow.reproduce_cell` re-renders a past execution;
``reproduce_cell(4, lookback=1)`` reaches the execution of cell 4 *before* the
latest one, which is how you recover a result an autosaved re-run replaced.
