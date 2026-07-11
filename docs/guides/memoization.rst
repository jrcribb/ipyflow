Memoization
===========

Put ``%%memoize`` at the top of a cell and ipyflow caches its results. On a later
run with the **same inputs and the same cell content**, it restores the cached
results instead of re-executing. You never declare the inputs -- ipyflow infers
them from the dataflow graph it already maintains.

.. cell::
   :reset:

   base = 3

.. cell::

   %%memoize
   scaled = base * 10

Run that cell once and ``scaled`` is computed normally. Re-run it unchanged and
ipyflow detects the identical inputs and reuses the cached result rather than
recomputing; change ``base`` (or the cell's code) and it recomputes. This is what
makes re-running expensive cells cheap when nothing they depend on has changed:

.. image:: https://raw.githubusercontent.com/ipyflow/ipyflow/master/img/ipyflow-memoization.gif
   :alt: A memoized cell reusing its cached result on re-run
   :width: 600
   :align: center

Memoization applies to cells whose values are functions, classes, primitives
(ints, floats, strings), numpy arrays, pandas dataframes, and containers of those.

Controlling replayed output
---------------------------

By default a cache hit replays only the displayhook value of the cell's last
expression, suppressing captured stdout/stderr and rich output. Two flags adjust
this:

- ``--quiet`` / ``-q`` -- suppress *all* output on replay.
- ``--verbose`` / ``-v`` -- replay everything: stdout, stderr, and rich display
  outputs, as if the cell had run.

.. code-block:: python

   %%memoize --verbose
   print("this line is replayed from cache on a hit")
   fig  # rich output replayed too

.. image:: https://raw.githubusercontent.com/ipyflow/ipyflow/master/img/memoize-quiet-verbose.gif
   :alt: The --quiet and --verbose memoization output levels
   :width: 600
   :align: center

Because a cache hit replays a cell's outputs verbatim, ``%%memoize`` pairs well
with ipywidgets and interactive plots: an expensive figure re-renders instantly
while its inputs are unchanged, and recomputes automatically once they change --
the basis for responsive dashboards on JupyterLab and ipyflow.
