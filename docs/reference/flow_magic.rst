The ``%flow`` magic
===================

``%flow`` is ipyflow's line magic for inspecting and configuring a session. It is
registered automatically when ipyflow loads. This page catalogs its subcommands;
several are demonstrated as executable examples elsewhere in these docs (see
:doc:`../guides/reactive_execution` and :doc:`../concepts/slicing`).

Any subcommand's output can be redirected to a file with a trailing ``> path``,
e.g. ``%flow slice 4 > slice.py``.

Inspecting the graph
--------------------

``%flow deps <symbol>``
    Print a symbol's immediate dependencies and dependents. Aliases:
    ``show_deps``, ``show_dependencies``.

``%flow code <symbol>``
    Print the backward slice (reconstructing code) for a symbol. Alias:
    ``get_code``. The programmatic equivalent is ``code(sym)``.

``%flow waiting [global|all]``
    List symbols that are waiting on newer dependencies (stale). ``global`` (the
    default) considers top-level names; ``all`` considers every alias. Alias:
    ``show_waiting``.

``%flow slice [<cell_num>]``
    Print the code needed to reconstruct a cell using dynamic program slicing.
    With no argument, slices the most recent cell. Aliases: ``make_slice``,
    ``gather_slice``. Options:

    - ``--stmt`` / ``--stmts`` -- slice at statement granularity (implies
      ``--blacken``).
    - ``--blacken`` -- reformat the result with ``black``.
    - ``--tag <tag>`` -- slice the cells carrying a tag instead of a cell number
      (a ``$``-prefixed tag additionally marks the current cell reactive for it).
    - ``--noheader`` -- omit the ``# Cell N`` headers.

    The standalone ``%histslice <cell_num>`` magic is shorthand for ``%flow slice
    --noheader <cell_num>``.

``%flow dag``
    Emit the cell DAG as JSON. Aliases: ``make_dag``, ``cell_dag``,
    ``make_cell_dag``.

Cell tags
---------

``%flow tag <name>``
    Tag the current cell (or the cell given by ``--cell <ctr>``). Pass
    ``--remove`` to remove the tag instead.

``%flow show_tags``
    Show the current cell's tags (or those of ``--cell <ctr>``).

Configuring the session
-----------------------

These map onto the enums in :doc:`config`:

``%flow mode [lazy|reactive]``
    Set the :class:`~ipyflow.config.ExecutionMode`. Aliases: ``exec_mode``
    (``normal`` is accepted as a synonym for ``lazy``).

``%flow schedule [liveness_based|dag_based|hybrid_dag_liveness_based]``
    Set the :class:`~ipyflow.config.ExecutionSchedule`. Aliases: ``exec_schedule``,
    ``execution_schedule``.

``%flow direction [in_order|any_order]``
    Set the :class:`~ipyflow.config.FlowDirection`. Aliases: ``order``,
    ``semantics``, ``flow_direction``, ``flow_order``, ``flow_semantics``;
    ``ordered`` / ``unordered`` / ``linear`` / ``both`` are accepted as values.

``%flow reactivity [batch|incremental]``
    Set the :class:`~ipyflow.config.ReactivityMode`. ``incremental`` requires a
    liveness-aware schedule and will upgrade ``dag_based`` automatically.

``%flow hls [all|none|executed|reactive]`` / ``%flow nohls``
    Set the :class:`~ipyflow.config.Highlights` mode (``nohls`` disables
    highlighting). Aliases: ``highlight``, ``highlights``.

Toggles and lifecycle
---------------------

``%flow enable`` / ``%flow disable``
    Turn dataflow capture on or off (on by default). Aliases: ``on`` / ``off``.

``%flow clear``
    Reset the staleness baseline to the current cell counter.

``%flow warn_ooo`` / ``%flow nowarn_ooo``
    Toggle warnings for out-of-order symbol usages.

``%flow lint_ooo`` / ``%flow nolint_ooo``
    Toggle linting of out-of-order usages.

``%flow syntax_transforms [on|off]``
    Enable or disable the source syntax transforms (including the ``$`` reactive
    syntax). ``%flow syntax_transforms_only`` keeps the transforms while disabling
    dataflow capture.

``%flow trace_messages [enable|disable]``
    Toggle verbose tracer message logging (a debugging aid).

Extensibility
-------------

``%flow register_tracer <module.path.to.TracerClass>``
    Register an additional pyccolo tracer for the session (``dataflow`` is a
    built-in alias for ipyflow's own tracer). Alias: ``register``.

``%flow deregister_tracer [<class>|all]``
    Deregister a previously registered tracer, or ``all`` of them. Alias:
    ``deregister``.

``%flow register_annotations <directory_or_file>``
    Register external-library dataflow annotations from a directory or ``.pyi``
    file.
