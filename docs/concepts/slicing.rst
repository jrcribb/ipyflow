Program slicing
===============

A **backward slice** of a value is the minimal subset of the program needed to
recompute it. Because ipyflow maintains a precise dataflow graph, it can slice at
the granularity of cells or individual statements, and it exposes slicing through
both the ``code`` API and the ``%flow slice`` magic. Slicing is what powers the
``code`` helper, the frontend's "get code" action, and reactive re-execution.

Cell-level slicing
------------------

``cells(n).slice()`` returns the slice needed to reconstruct cell ``n``. Only the
cells that ``n`` transitively depends on are included; unrelated cells are
dropped. Here cell 2 is never referenced by cell 3, so it does not appear in the
slice:

.. testcode::

   run_cell("x = 0")
   run_cell("unused = 999")
   run_cell("y = x + 1")
   run_cell("print(cells(3).slice())")

.. testoutput::

   # Cell 1
   x = 0

   # Cell 3
   y = x + 1

The equivalent from the magic side is ``%flow slice 3`` (with no cell number it
slices the most recent cell). The magic prints the same reconstructed source and
can additionally write it to a file with ``%flow slice 3 > out.py``.

Symbol-level slicing
--------------------

The ``code`` helper slices for a *symbol* rather than a cell -- otherwise
identical:

.. testcode::

   run_cell = reset_flow()  # start this example from a clean notebook
   run_cell("a = 10")
   run_cell("b = a * 2")
   run_cell("assert str(code(b)) == '# Cell 1\\na = 10\\n\\n# Cell 2\\nb = a * 2'")

Statement-level slicing
-----------------------

Cell-level slices always include *whole* cells. Statement-level slicing goes
finer, dropping individual statements a value does not depend on. Add ``--stmt``
to ``%flow slice``. Below, ``final`` depends on ``mid`` (hence ``keep``) but not
on ``junk``, so the statement slice omits ``junk = 2`` even though it shares a
cell with the needed statements:

.. testcode::

   run_cell = reset_flow()  # start this example from a clean notebook
   run_cell("keep = 1\njunk = 2\nmid = keep + 10")
   run_cell("final = mid + 1")
   run_cell("get_ipython().run_line_magic('flow', 'slice --stmt 2')")

.. testoutput::

   # Cell 1
   keep = 1
   mid = keep + 10

   # Cell 2
   final = mid + 1

``--stmt`` implies re-formatting the result with ``black`` (also available on its
own as ``--blacken``) so the extracted statements read cleanly.

Static vs. dynamic slicing
--------------------------

ipyflow can derive edges two ways, corresponding to the two
:class:`~ipyflow.slicing.context.SlicingContext` modes:

- **Dynamic slicing** uses edges observed during actual execution. It is the most
  precise, since it reflects what really happened at runtime, and is enabled by
  default (``dynamic_slicing_enabled``).
- **Static slicing** uses edges inferred from source-code liveness analysis --
  which symbols each statement reads and writes -- without running it
  (``static_slicing_enabled``). This is what makes the ``liveness_based``
  execution schedule possible when runtime edges are unavailable.

Both can be active at once; ipyflow unions their edges when computing a slice.
:meth:`MutableDataflowSettings.slicing_contexts
<ipyflow.config.MutableDataflowSettings>` reports which contexts are currently
enabled. The relationship to scheduling is covered in
:doc:`../guides/reactive_execution`.
