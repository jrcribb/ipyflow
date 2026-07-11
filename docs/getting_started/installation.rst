Installation
============

ipyflow ships as a single PyPI distribution that pulls in the ``ipyflow-core``
backend, the JupyterLab/Notebook 7 extension, and a Jupyter kernelspec:

.. code-block:: bash

   pip install ipyflow

This registers a kernel named **Python 3 (ipyflow)**. In JupyterLab or Notebook 7
pick it from the Launcher, or switch an open notebook to it via *Kernel → Change
Kernel*. Because ipyflow is a strict superset of ``ipykernel``, existing
notebooks run unchanged -- you simply gain the dataflow features on top.

Requirements
------------

ipyflow supports CPython 3.7+ (declared support goes back to 3.6; CI exercises
3.7 through 3.14). The frontend features target JupyterLab 3/4 and Notebook 7.

Installing the kernelspec manually
----------------------------------

``pip install ipyflow`` installs the kernelspec for you. If you need to
(re)install it into a specific environment -- for example inside a container, or
after moving a virtualenv -- invoke the installer module directly:

.. code-block:: bash

   python -m ipyflow.install --sys-prefix

``--sys-prefix`` installs into the active environment's prefix (the usual choice
inside a virtualenv or conda env); omit it to install into the user location, or
pass ``--prefix`` to target an arbitrary directory. This is the same entry point
the packaging invokes, exposed as ``ipyflow.install``.

Using ipyflow outside JupyterLab
--------------------------------

The reactive UI (dependency dots, reactive re-execution, autosave) requires the
JupyterLab/Notebook 7 extension. On surfaces where that extension is not yet
available -- Colab, VS Code, a plain terminal IPython, or a raw Jupyter Console
-- you can still load ipyflow's tracer and use its full dataflow **API** by
loading it as an IPython extension:

.. code-block:: python

   %pip install ipyflow
   %load_ext ipyflow

``%load_ext ipyflow`` swaps in ipyflow's kernel/shell machinery for the current
session (see :func:`ipyflow.load_ipython_extension`), after which ``deps``,
``users``, ``code``, ``%flow``, ``%%memoize``, and the rest behave as documented
here. Reactive *execution* and the visual highlights, however, remain a
frontend-driven feature.

Trying it without installing
----------------------------

A zero-install build runs entirely in the browser via JupyterLite (Pyodide):

  https://ipyflow.github.io/ipyflow/lab/index.html?path=demo.ipynb

It is the quickest way to get a feel for reactive execution before adopting
ipyflow locally.

Next: :doc:`first_notebook` walks through building a small reactive notebook and
inspecting the dataflow graph it produces.
