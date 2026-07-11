ipyflow
=======

**ipyflow** is a next-generation Python kernel for JupyterLab and Notebook 7 that
tracks fine-grained dataflow relationships between the symbols and cells of an
interactive session. It uses `pyccolo <https://pyccolo.readthedocs.io>`_ to
instrument executing code, building a live dataflow graph that powers reactive
execution, staleness detection, program slicing, and memoization -- all as a
*drop-in* superset of the stock ``ipykernel``.

Where the `README <https://github.com/ipyflow/ipyflow>`_ gives the tour and the
screenshots, this documentation is a code-level reference: it explains the
model ipyflow builds, documents the programmatic dataflow API, and catalogs the
``%flow`` magic. Every worked example below is executed against a live ipyflow
kernel when the docs are built (via ``sphinx.ext.doctest``), so what you read is
what the current release actually does.

A taste
-------

ipyflow watches assignments and usages as cells run and records who depends on
whom. The programmatic API lets you interrogate that graph directly:

.. testcode::

   run_cell("x = 0")
   run_cell("y = x + 1")

   # `deps` / `users` report the immediate neighbors in the dataflow graph.
   run_cell("assert deps(y) == [lift(x)]")
   run_cell("assert users(x) == [lift(y)]")

   # `code` reconstructs the minimal program slice that produces a symbol.
   run_cell("assert str(code(y)) == '# Cell 1\\nx = 0\\n\\n# Cell 2\\ny = x + 1'")

Each ``run_cell(...)`` above stands in for executing a notebook cell. In a real
JupyterLab session you would simply type the code into cells; ipyflow tracks the
same graph either way.

Why ipyflow
-----------

- **Precise dependency inference.** ipyflow understands dependencies below the
  variable level -- it knows cell ``B`` depends on ``x[0]`` and will not react to
  an unrelated change to ``x[1]``, keeping re-execution to a minimum.
- **Fearless execution.** With reactive mode enabled, executing any cell makes
  its output (and that of its upstream and downstream cells) appear exactly as it
  would after a *restart-and-run-all*.
- **A queryable model.** The same graph that drives the UI is available to you as
  a Python API, so you can slice, trace provenance, and recover prior outputs
  programmatically.

Try it in the browser (no install) via the
`JupyterLite demo <https://ipyflow.github.io/ipyflow/lab/index.html?path=demo.ipynb>`_.

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   getting_started/installation
   getting_started/first_notebook

.. toctree::
   :maxdepth: 2
   :caption: Guides

   guides/reactive_execution
   guides/introspection_api
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
