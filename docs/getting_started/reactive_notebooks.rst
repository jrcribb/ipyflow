Reactive notebooks
==================

The core idea behind ipyflow is simple: as you run cells, it watches how values
flow between them and remembers which cells depend on which. That knowledge lets
it keep your notebook *consistent* -- so that what you see always matches what a
clean top-to-bottom run would produce -- without you having to track dependencies
in your head.

This page is a tour of what that looks like in JupyterLab. Later pages cover the
:doc:`execution settings <../guides/execution>` and the :doc:`programmatic API
<../guides/dataflow_api>` in depth.

Seeing dependencies
-------------------

Whenever you select a cell, ipyflow marks the cells related to it. Cells that
would need to re-run if you re-ran the selected one get an **orange** dot; cells
it depends on that are already up to date get a **purple** dot:

.. image:: https://raw.githubusercontent.com/ipyflow/ipyflow/master/img/ipyflow-dots.gif
   :alt: Dependency dots highlighting related cells as you select a cell
   :width: 500
   :align: center

These dots come from the same dataflow graph that powers everything else, and
they update live as you edit and execute. They tell you, at a glance, what is
affected by a change -- even in a long notebook where the related cells are far
apart.

Reactive execution
------------------

Reactivity is **opt-in**. By default ipyflow behaves like a normal kernel and runs
only the cell you execute. Turn reactive execution on with the ``%flow`` magic:

.. code-block:: python

   %flow mode reactive

Now, running a cell also re-runs the (minimal) set of upstream and downstream
cells that are out of sync, in dependency order, so the whole notebook reflects a
consistent state:

.. image:: https://raw.githubusercontent.com/ipyflow/ipyflow/master/img/ipyflow-tldr.gif
   :alt: Running one cell reactively re-runs its dependent cells
   :width: 600
   :align: center

Switch back to normal execution any time with ``%flow mode lazy``. If you would
rather keep the default lazy behavior but occasionally run a single cell *and* its
dependents, use **ctrl+shift+enter** (**cmd+shift+enter** on macOS) for a one-off
reactive execution:

.. image:: https://raw.githubusercontent.com/ipyflow/ipyflow/master/img/alt-mode-execute.gif
   :alt: Using ctrl+shift+enter for a one-off reactive execution
   :width: 600
   :align: center

Because the dependency information is saved into the notebook, you can reopen a
notebook, jump straight to a cell, run it, and trust that its output reflects the
author's intent -- ipyflow brings the prerequisites up to date for you:

.. image:: https://raw.githubusercontent.com/ipyflow/ipyflow/master/img/ipyflow-restart.gif
   :alt: Jumping to a cell after a restart and getting consistent output
   :width: 500
   :align: center

Staleness at a glance
---------------------

When a cell references data that has since been updated elsewhere, its input
collapser turns orange, and cells that depend on it turn purple -- a visual
warning that outputs may be out of sync. In reactive mode you rarely see these,
because the stale cells re-run automatically; you will notice them if you opt out
of reactivity for a run, or overwrite the data a cell produces.

If inconsistencies do pile up, you don't have to hunt them down. Press **Space**
in command mode and ipyflow resolves all stale and dirty cells for you, repeating
until the notebook is consistent:

.. image:: https://raw.githubusercontent.com/ipyflow/ipyflow/master/img/resolve-inconsistencies.gif
   :alt: Pressing Space to resolve stale and dirty cells
   :width: 500
   :align: center

Recovering overwritten output
-----------------------------

To keep the on-disk notebook, the UI, and the kernel in sync, ipyflow enables
autosave-on-change. If a reactive re-run overwrites an output you wanted to keep,
you can recover the input and output of a previous cell execution -- within the
session -- with :func:`~ipyflow.reproduce_cell`:

.. code-block:: python

   from ipyflow import reproduce_cell
   reproduce_cell(4, lookback=1)  # the execution of cell 4 before the latest one

.. image:: https://raw.githubusercontent.com/ipyflow/ipyflow/master/img/reproduce-cell.gif
   :alt: Recovering a previous cell execution with reproduce_cell
   :width: 500
   :align: center

Working with widgets
--------------------

ipyflow's reactive engine understands ``ipywidgets``: changing a widget can drive
updates across cell boundaries, which -- combined with :doc:`memoization
<../guides/memoization>` -- makes it practical to build responsive, near
real-time dashboards on top of JupyterLab.

.. image:: https://raw.githubusercontent.com/ipyflow/ipyflow/master/img/ipywidgets-integration.gif
   :alt: Widget changes propagating reactively across cells
   :width: 500
   :align: center

Where to next
-------------

- :doc:`../guides/execution` -- tune how reactivity behaves: lazy vs. reactive,
  in-order vs. any-order, and the execution schedule.
- :doc:`../guides/dataflow_api` -- query the dataflow graph from Python: inspect
  dependencies, reconstruct code, tag symbols, set watchpoints.
- :doc:`../guides/memoization` -- skip recomputation with ``%%memoize``.
- :doc:`../concepts/dataflow_model` -- how ipyflow builds and reasons about the
  graph under the hood.
