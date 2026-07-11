Configuration (``ipyflow.config``)
==================================

ipyflow's per-session behavior is governed by a handful of enums and the
:class:`~ipyflow.config.MutableDataflowSettings` dataclass that holds them. Each
enum has a default (used when an unrecognized value is supplied) and a
corresponding ``%flow`` subcommand.

Settings can be changed at runtime with the ``%flow`` magic
(:doc:`flow_magic`), read or written on ``flow().mut_settings``, or set as
defaults in your IPython profile via ``c.ipyflow.<name> = ...``.

Enum ↔ ``%flow`` subcommand
---------------------------

============================  ================================  ==========================================
Enum                          Default                           ``%flow`` subcommand
============================  ================================  ==========================================
:class:`ExecutionMode`        ``lazy``                          ``%flow mode [lazy|reactive]``
:class:`ExecutionSchedule`    ``dag_based``                     ``%flow schedule [liveness_based|dag_based|hybrid_dag_liveness_based]``
:class:`FlowDirection`        ``in_order``                      ``%flow direction [in_order|any_order]``
:class:`ReactivityMode`       ``batch``                         ``%flow reactivity [batch|incremental]``
:class:`Highlights`           ``executed``                      ``%flow hls [all|none|executed|reactive]`` / ``%flow nohls``
============================  ================================  ==========================================

Enums
-----

.. autoclass:: ipyflow.config.ExecutionMode
   :members:
   :undoc-members:

.. autoclass:: ipyflow.config.ExecutionSchedule
   :members:
   :undoc-members:

.. autoclass:: ipyflow.config.FlowDirection
   :members:
   :undoc-members:

.. autoclass:: ipyflow.config.ReactivityMode
   :members:
   :undoc-members:

.. autoclass:: ipyflow.config.Highlights
   :members:
   :undoc-members:

Settings
--------

The mutable per-session settings live on ``flow().mut_settings``. Beyond the enums
above it exposes toggles such as ``dataflow_enabled``, ``static_slicing_enabled``,
``dynamic_slicing_enabled``, ``warn_out_of_order_usages``, and
``syntax_transforms_enabled``.

.. autoclass:: ipyflow.config.MutableDataflowSettings
   :members: slicing_contexts
