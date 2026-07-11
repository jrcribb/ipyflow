Reactive execution
===================

ipyflow's headline feature is *reactive execution*: run a cell and let ipyflow
re-run exactly the other cells that need it, so the notebook always looks as
though it were run top to bottom. This behavior is governed by three orthogonal
settings -- the **execution mode**, the **flow direction**, and the **execution
schedule** -- plus an inline **reactive-variable syntax**. This guide covers each.

All four are also settable per session with the ``%flow`` magic (see
:doc:`../reference/flow_magic`) or made the default in your IPython profile.

Execution mode: lazy vs. reactive
---------------------------------

The execution mode is an :class:`~ipyflow.config.ExecutionMode`:

``lazy`` (the default)
    Only the cell you execute runs. ipyflow still tracks dependencies and flags
    stale cells in the UI, but it does not act on them. This is the fully
    backwards-compatible ``ipykernel`` behavior.

``reactive``
    Executing a cell also re-executes its stale upstream and downstream cells, in
    dependency order.

Switch modes at runtime with ``%flow mode``; the change is reflected on
``flow().mut_settings``:

.. testcode::

   run_cell("from ipyflow import flow")
   run_cell("get_ipython().run_line_magic('flow', 'mode reactive')")
   run_cell("assert flow().mut_settings.exec_mode.value == 'reactive'")

   run_cell("get_ipython().run_line_magic('flow', 'mode lazy')")
   run_cell("assert flow().mut_settings.exec_mode.value == 'lazy'")

Even in lazy mode you can reactively execute a *single* cell on demand with
**ctrl+shift+enter** (or **cmd+shift+enter** on macOS), which runs that cell plus
its dependents without changing the default mode. When the default *is* reactive,
the same shortcut inverts to a one-off non-reactive run.

To make reactive mode the default for every new kernel, add to your IPython
profile (usually ``~/.ipython/profile_default/ipython_config.py``):

.. code-block:: python

   c = get_config()
   c.ipyflow.exec_mode = "reactive"  # defaults to "lazy"

Flow direction: in-order vs. any-order
--------------------------------------

The flow direction is a :class:`~ipyflow.config.FlowDirection` that decides which
dataflow edges are eligible to drive reactive execution:

``in_order`` (the default)
    A cell may only reactively trigger cells that appear *after* it in the
    notebook. ipyflow still tracks backward references (a cell using a symbol
    defined later), but omits those edges when scheduling reactivity.

``any_order``
    Spatial position is ignored; any dependency edge can drive reactivity.

In-order semantics are less flexible but encourage cleaner, reproducible
notebooks that convert cleanly to top-to-bottom scripts. Toggle with ``%flow
direction`` (aliases: ``order``, ``semantics``; values also accept ``ordered`` /
``unordered``):

.. testcode::

   run_cell("from ipyflow import flow")
   run_cell("get_ipython().run_line_magic('flow', 'direction any_order')")
   run_cell("assert flow().mut_settings.flow_order.value == 'any_order'")

   run_cell("get_ipython().run_line_magic('flow', 'direction in_order')")
   run_cell("assert flow().mut_settings.flow_order.value == 'in_order'")

Or set the default in your profile:

.. code-block:: python

   c = get_config()
   c.ipyflow.flow_direction = "any_order"  # defaults to "in_order"

Execution schedule
------------------

The schedule is an :class:`~ipyflow.config.ExecutionSchedule` controlling *how*
the set of cells to re-run is computed:

``dag_based`` (the default)
    Uses the dynamic dataflow DAG built from actual runtime dependencies. The most
    precise option.

``liveness_based``
    Uses static liveness analysis of cell source (which symbols each cell reads
    and writes). Useful when runtime edges are unavailable -- for instance the
    JupyterLite/Pyodide build defaults to this.

``hybrid_dag_liveness_based``
    Combines both; required for incremental reactivity (see below).

.. testcode::

   run_cell("from ipyflow import flow")
   run_cell("get_ipython().run_line_magic('flow', 'schedule liveness_based')")
   run_cell("assert flow().mut_settings.exec_schedule.value == 'liveness_based'")

A related knob, :class:`~ipyflow.config.ReactivityMode` (``%flow reactivity
[batch|incremental]``), chooses whether reactive updates are applied all at once
(``batch``, the default) or one cell at a time (``incremental``). Incremental
mode requires a liveness-aware schedule; selecting it while on ``dag_based``
automatically upgrades the schedule to ``hybrid_dag_liveness_based``.

Reactive-variable syntax
------------------------

Reactivity is normally *cell-level*. The ``$`` prefix opts an individual symbol
into reactivity so that updates propagate even in lazy mode:

.. code-block:: text

   # Cell 1
   x = 1

   # Cell 2 -- `$x` marks this usage as reactive
   y = $x + 1

   # Now re-running Cell 1 with a new value reactively refreshes Cell 2,
   # even though the global execution mode is still lazy.

A double prefix, ``$$x``, additionally makes the *definition* cascade: downstream
reactive readers update transitively. The ``$`` syntax is applied by ipyflow's
input transformer in the JupyterLab/Notebook frontend; because it is a
frontend-level source rewrite it is demonstrated here as prose rather than an
executed example.

.. seealso::

   :doc:`../reference/config` for the full enum reference and
   :doc:`../reference/flow_magic` for every ``%flow`` subcommand that toggles
   these settings.
