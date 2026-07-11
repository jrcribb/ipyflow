Model accessors (``ipyflow.models``)
====================================

These functions, also re-exported from the top-level ``ipyflow`` package, are the
entry points to ipyflow's data model. Most return a *class* whose classmethods
query the whole graph; a few return a specific instance relative to the active
cell.

Two accessors are overloaded. ``cells()`` with no argument returns the
:class:`~ipyflow.data_model.cell.Cell` class, while ``cells(cell_id)`` returns a
single ``Cell``; likewise ``symbols()`` returns the
:class:`~ipyflow.data_model.symbol.Symbol` class, while ``symbols(sym)`` passes an
instance through unchanged.

.. automodule:: ipyflow.models
   :members: cells, cell_above, cell_below, cell_at_offset, last_run_cell,
             symbols, namespaces, scopes, statements, timestamps

.. seealso::

   :doc:`data_model` for the classes these accessors expose.
