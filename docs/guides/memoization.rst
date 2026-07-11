Memoization
===========

The ``%%memoize`` pseudo-magic caches a cell's results in memory and, on a later
run with **identical inputs and identical cell content**, restores those results
instead of re-executing. Unlike ordinary function memoization you never declare
the inputs -- ipyflow infers them from the dataflow graph it is already
maintaining.

Memoization applies to cells whose values are functions, classes, primitives
(ints, floats, strings), numpy arrays, pandas dataframes, and containers of
those. It is written as the first line of a cell:

.. code-block:: python

   %%memoize
   df = expensive_load()
   result = transform(df)

How reuse is decided
--------------------

``%%memoize`` is not a registered magic in the usual sense -- ipyflow detects the
directive by inspecting a cell's first line (see
:meth:`Cell.get_memoized_content_and_output_level
<ipyflow.data_model.cell.Cell>`) and keys the cache on the identity of the
symbols the cell reads plus the cell's source. When both match a prior run of the
same cell, the cached outputs are replayed.

You can observe the decision through the cell object: ``cells(id).is_memoized``
reports that a cell is a memoization cell, and
``cells(id).skipped_due_to_memoization_ctr`` is ``-1`` when the cell actually ran
and a positive counter when a cached result was reused.

The example below runs a memoized cell, re-runs it unchanged (a cache hit), then
changes an input (forcing a real re-run). ``run_cell`` accepts a ``cell_id`` so
we can re-run *the same* cell, which is what memoization keys on:

.. testcode::

   import contextlib, io

   # First run: the cell executes, so nothing is skipped.
   run_cell("base = 3", cell_id="input")
   run_cell("%%memoize\nscaled = base * 10", cell_id="calc")
   run_cell("assert scaled == 30")
   run_cell("assert cells('calc').is_memoized")
   run_cell("assert cells('calc').skipped_due_to_memoization_ctr == -1")

   # Re-run with identical inputs and content: the cached result is reused. On a
   # hit ipyflow prints a short "reusing memoized result" status line, suppressed
   # here so the example stays deterministic.
   run_cell("base = 3", cell_id="input")
   with contextlib.redirect_stdout(io.StringIO()):
       run_cell("%%memoize\nscaled = base * 10", cell_id="calc")
   run_cell("assert cells('calc').skipped_due_to_memoization_ctr > 0")
   run_cell("assert scaled == 30")

   # Change an input: the cache is invalidated and the cell runs again.
   run_cell("base = 5", cell_id="input")
   run_cell("%%memoize\nscaled = base * 10", cell_id="calc")
   run_cell("assert cells('calc').skipped_due_to_memoization_ctr == -1")
   run_cell("assert scaled == 50")

Controlling replayed output
---------------------------

By default ``%%memoize`` replays only the displayhook value of the cell's final
expression, suppressing captured stdout/stderr and rich display output. Two flags
adjust this verbosity (an :class:`~ipyflow.memoization.MemoizedOutputLevel`):

``--quiet`` / ``-q``
    Suppress *all* output on replay, including the final expression.

``--verbose`` / ``-v``
    Replay everything -- stdout, stderr, and rich display outputs -- as if the
    cell had run.

.. code-block:: python

   %%memoize --verbose
   print("this stdout is replayed from cache on a hit")
   fig  # rich output replayed too

Combining with widgets
-----------------------

Because a cache hit replays a cell's outputs verbatim, ``%%memoize`` pairs well
with ipywidgets and interactive plots: expensive figures render near-instantly on
replay while their upstream data is unchanged, and re-render automatically once an
input does change. This is the basis for building responsive dashboards on top of
JupyterLab and ipyflow.
