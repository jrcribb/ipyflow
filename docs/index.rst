ipyflow
=======

**ipyflow** is a reactive Python kernel for JupyterLab and Notebook 7. As you run
cells, it tracks how values flow between them and builds a live dataflow graph --
which it uses to keep your notebook consistent: run any cell and its outputs (and
those of the cells it depends on) appear as they would after a clean
*restart-and-run-all*. It's a drop-in superset of the standard ``ipykernel``, so
your notebooks keep working exactly as before.

.. image:: https://raw.githubusercontent.com/ipyflow/ipyflow/master/img/ipyflow-tldr.gif
   :alt: Running one cell reactively updates the cells that depend on it
   :width: 600
   :align: center

Two minutes in
--------------

.. code-block:: bash

   pip install ipyflow

Then pick **Python 3 (ipyflow)** from the Launcher and start a notebook. The
:doc:`getting_started/reactive_notebooks` tour shows what reactive execution looks
like; the rest of these docs go deep on the settings, the programmatic dataflow
API, and how the model works underneath.

Prefer to poke at it first? A full ipyflow runs in your browser with no install
via the `JupyterLite demo
<https://ipyflow.github.io/ipyflow/lab/index.html?path=demo.ipynb>`_.

The graph, from Python
----------------------

The same dataflow graph that drives the UI is queryable. For example, ``deps``
reports a value's immediate dependencies:

.. cell::
   :reset:

   x = 0

.. cell::

   y = x + 1

.. cell::

   print(deps(y))

.. cell-output::

   [<x>]

Every worked example in these docs -- like the one above -- is executed against a
live ipyflow kernel when the docs are built, so what you read matches what the
current release actually does.

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   getting_started/installation
   getting_started/reactive_notebooks

.. toctree::
   :maxdepth: 2
   :caption: Guides

   guides/execution
   guides/dataflow_api
   guides/memoization

.. toctree::
   :maxdepth: 2
   :caption: How it works

   concepts/dataflow_model
   concepts/slicing

.. toctree::
   :maxdepth: 2
   :caption: Reference

   reference/api
   reference/models
   reference/config
   reference/flow_magic
   reference/data_model

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
