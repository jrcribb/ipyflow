Execution settings
==================

Three settings shape how ipyflow schedules work: the **execution mode** (does
running a cell re-run its dependencies?), the **flow direction** (which
dependencies count?), and the **execution schedule** (how is the set to re-run
computed?). Each is a one-liner with the ``%flow`` magic, and each can be made the
default in your IPython profile.

Lazy vs. reactive
-----------------

By default ipyflow is **lazy**: running a cell runs only that cell, just like the
stock kernel. Switch to **reactive** so that running a cell also re-runs its stale
upstream and downstream cells:

.. cell::

   %flow mode reactive

Go back to the default with ``%flow mode lazy``:

.. cell::

   %flow mode lazy

.. image:: https://raw.githubusercontent.com/ipyflow/ipyflow/master/img/reactivity-opt-out.gif
   :alt: Toggling reactive execution on and off with the %flow magic
   :width: 600
   :align: center

To make reactive mode the default for every new kernel, add to your IPython
profile (usually ``~/.ipython/profile_default/ipython_config.py``):

.. code-block:: python

   c = get_config()
   c.ipyflow.exec_mode = "reactive"  # defaults to "lazy"

In-order vs. any-order
----------------------

The flow direction decides which dependency edges are allowed to drive reactive
execution. The default is **in-order**: a cell may only trigger cells *below* it,
so reactivity follows the notebook's top-to-bottom reading order. ipyflow still
tracks references to data defined later, but leaves those edges out when
scheduling. Switch to **any-order** to let any dependency drive reactivity,
regardless of position:

.. cell::

   %flow direction any_order

.. image:: https://raw.githubusercontent.com/ipyflow/ipyflow/master/img/ipyflow-direction.gif
   :alt: Switching between in-order and any-order flow semantics
   :width: 600
   :align: center

In-order semantics are a little less flexible but encourage cleaner, reproducible
notebooks that convert directly to top-to-bottom scripts. Return to the default
with ``%flow direction in_order``, or set it in your profile:

.. code-block:: python

   c = get_config()
   c.ipyflow.flow_direction = "any_order"  # defaults to "in_order"

Execution schedule
------------------

The schedule controls how the set of cells to re-run is computed:

- **dag_based** (the default) uses the dynamic dataflow graph -- the most precise
  option, since it reflects what actually happened at runtime.
- **liveness_based** uses static analysis of cell source (which symbols each cell
  reads and writes), which is handy when runtime edges aren't available -- the
  in-browser JupyterLite build uses it, for example.
- **hybrid_dag_liveness_based** combines the two.

.. cell::

   %flow schedule liveness_based

A companion setting, ``%flow reactivity``, chooses whether reactive updates are
applied all at once (``batch``, the default) or one cell at a time
(``incremental``). Incremental updates need a liveness-aware schedule; selecting
them automatically upgrades a ``dag_based`` schedule to
``hybrid_dag_liveness_based``.

.. cell::

   %flow reactivity incremental

See :doc:`../reference/flow_magic` for the full ``%flow`` command reference and
:doc:`../reference/config` for the settings enums and their defaults.
