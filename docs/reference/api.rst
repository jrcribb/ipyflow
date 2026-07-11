Reactive API (``ipyflow.api``)
==============================

These are the user-facing helpers re-exported at the top level of ``ipyflow``
(``from ipyflow import deps, users, code, ...``). Each symbol-introspection helper
takes the *value* of a notebook symbol; a tracer hook resolves it to the
corresponding :class:`~ipyflow.data_model.symbol.Symbol`. See
:doc:`../guides/introspection_api` for worked examples.

Symbol introspection
--------------------

.. automodule:: ipyflow.api.lift
   :members:
   :undoc-members:

Cell output recovery
--------------------

.. automodule:: ipyflow.api.cells
   :members:
