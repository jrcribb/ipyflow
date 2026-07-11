# -*- coding: utf-8 -*-
"""Sphinx directives for natural, copy-pasteable -- yet doctested -- notebook cells.

A ``.. cell::`` block renders as an ordinary, copy-pasteable Python code block, and
is *also* executed through a live ipyflow kernel when the ``doctest`` builder runs
(see ``ipyflow_doctest.py``). Readers see real notebook code; the execution that
guards against drift happens invisibly. ``.. cell-output::`` shows -- and verifies
-- the output of the preceding cell.

Each ``.. cell::`` corresponds to one notebook cell. Add ``:reset:`` to the first
cell of an independent example to start from a fresh kernel (so its cell numbers
begin at 1); this only affects execution and is never shown to readers.
"""
from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective


def _hidden_test_node(code: str, testnodetype: str, language: str) -> nodes.Node:
    # A ``comment`` node carrying ``testnodetype`` is picked up by the doctest
    # builder but rendered by no builder -- exactly how sphinx.ext.doctest models
    # a ``:hide:``-den test block.
    node = nodes.comment(code, code, testnodetype=testnodetype, groups=["default"])
    node["options"] = {}
    node["language"] = language
    return node


class CellDirective(SphinxDirective):
    """A notebook cell: shown as copy-pasteable code, executed via the kernel."""

    has_content = True
    option_spec = {"reset": directives.flag}

    def run(self) -> list:
        code = "\n".join(self.content)
        display = nodes.literal_block(code, code)
        display["language"] = "python"
        display["classes"].append("ipyflow-cell")
        self.set_source_info(display)

        prefix = "run_cell = reset_flow()\n" if "reset" in self.options else ""
        exec_code = f"{prefix}run_cell({code!r})"
        test = _hidden_test_node(exec_code, "testcode", "python")
        self.set_source_info(test)
        return [display, test]


class CellOutputDirective(SphinxDirective):
    """The output of the preceding :rst:dir:`cell`, shown and verified."""

    has_content = True

    def run(self) -> list:
        text = "\n".join(self.content)
        display = nodes.literal_block(text, text)
        display["language"] = "none"
        display["classes"].append("ipyflow-output")
        self.set_source_info(display)

        out = _hidden_test_node(text, "testoutput", "none")
        self.set_source_info(out)
        return [display, out]


def setup(app):
    app.add_directive("cell", CellDirective)
    app.add_directive("cell-output", CellOutputDirective)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
