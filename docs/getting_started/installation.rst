Installation
============

.. code-block:: bash

   pip install ipyflow

That's it. Installing ipyflow registers a Jupyter kernel called **Python 3
(ipyflow)** and a JupyterLab / Notebook 7 extension automatically. Open the
Launcher (or *Kernel → Change Kernel* in an existing notebook) and pick **Python 3
(ipyflow)**:

.. image:: https://raw.githubusercontent.com/ipyflow/ipyflow/master/img/ipyflow-launcher.png
   :alt: Selecting the Python 3 (ipyflow) kernel from the JupyterLab launcher
   :width: 400
   :align: center

ipyflow is a drop-in superset of the standard ``ipykernel``, so your existing
notebooks run exactly as before -- you just gain the reactive and dataflow
features described in the rest of these docs.

Prefer to try before installing? A full ipyflow runs in your browser, no setup
required, via the `JupyterLite demo
<https://ipyflow.github.io/ipyflow/lab/index.html?path=demo.ipynb>`_.

Other environments
------------------

The reactive UI lives in the JupyterLab / Notebook 7 extension. On surfaces where
that extension isn't available yet -- Colab, VS Code, a terminal IPython -- you can
still load ipyflow's tracer and use its full dataflow **API** by loading it as an
IPython extension at the top of your session:

.. code-block:: python

   %pip install ipyflow
   %load_ext ipyflow

After that, ``deps``, ``code``, ``%flow``, ``%%memoize``, and everything else in
these docs work as described; only the visual highlights and automatic reactive
re-execution remain frontend features.
