import { expect, test } from '@jupyterlab/galata';

import {
  attachNotebookDumpOnFailure,
  cellClassList,
  cellLocator,
  cellSource,
  openIpyflowNotebook,
  setCellSource,
  settleAutosave,
  waitForCellClass,
  waitForEdge
} from './helpers';

/**
 * End-to-end coverage of ipyflow's cell decorations (ui/decorations.ts), which
 * are driven off the store's `changed` signal and applied as CSS classes on the
 * `.jp-Cell` nodes:
 *
 *   - slice visualization: the active/selected cell's forward execute-slice is
 *     tagged `ipyflow-slice-execute` and the backward dependency slice
 *     `ipyflow-slice`, updating live as the selection moves;
 *   - staleness: a directly-stale dependent is a `ready-making`/`ready-cell`,
 *     while a transitively-stale dependent is a `waiting-cell`.
 *
 * We read the class list straight off the widget node (cellClassList) so the
 * membership checks are exact.
 */
test.describe('ipyflow decorations', () => {
  attachNotebookDumpOnFailure(test);

  test.beforeEach(() => {
    test.setTimeout(120_000);
  });

  test('highlights the forward execute-slice and backward slice of the selection', async ({
    page
  }) => {
    // x -> y -> z chain plus an independent w.
    await openIpyflowNotebook(page, [
      'x = 1',
      'y = x + 1',
      'z = y + 1',
      'w = 10'
    ]);
    for (let i = 0; i < 4; i++) {
      await page.notebook.runCell(i);
    }
    await waitForEdge(page, 0, 1);
    await waitForEdge(page, 1, 2);

    // Selecting y: its forward slice {y, z} is the execute-slice; its ancestor x
    // is the (non-executing) dependency slice; the independent w is untouched.
    await page.notebook.selectCells(1);
    await waitForCellClass(page, 1, 'ipyflow-slice-execute');
    await waitForCellClass(page, 2, 'ipyflow-slice-execute');
    expect(await cellClassList(page, 0)).toContain('ipyflow-slice');
    expect(await cellClassList(page, 0)).not.toContain('ipyflow-slice-execute');
    expect(await cellClassList(page, 3)).not.toContain('ipyflow-slice');
    expect(await cellClassList(page, 3)).not.toContain('ipyflow-slice-execute');

    // Selecting x: the whole chain {x, y, z} becomes the execute-slice (x has no
    // ancestors, so there is no separate backward slice); w stays untouched.
    await page.notebook.selectCells(0);
    await waitForCellClass(page, 0, 'ipyflow-slice-execute');
    await waitForCellClass(page, 1, 'ipyflow-slice-execute');
    await waitForCellClass(page, 2, 'ipyflow-slice-execute');
    expect(await cellClassList(page, 3)).not.toContain('ipyflow-slice-execute');

    await settleAutosave(page);
  });

  test('distinguishes a directly-stale (ready) dependent from a transitively-stale (waiting) one', async ({
    page
  }) => {
    await openIpyflowNotebook(page, ['x = 1', 'y = x + 1', 'z = y + 1']);
    for (let i = 0; i < 3; i++) {
      await page.notebook.runCell(i);
    }
    await waitForEdge(page, 0, 1);
    await waitForEdge(page, 1, 2);

    // Re-run the root with a new value, without re-running its dependents. y
    // (direct child) is now ready to re-run; z (transitive child, still built
    // from the now-stale y) is waiting.
    await setCellSource(page, 0, 'x = 2');
    expect(await cellSource(page, 0)).toBe('x = 2');
    await page.notebook.runCell(0);

    await waitForCellClass(page, 2, 'waiting-cell');
    // The direct child is flagged ready-making, and is NOT a waiting cell.
    await waitForCellClass(page, 1, 'ready-cell');
    expect(await cellClassList(page, 1)).toContain('ready-making-input-cell');
    expect(await cellClassList(page, 1)).not.toContain('waiting-cell');

    await settleAutosave(page);
  });

  test('hovering a stale cell highlights its linked cells', async ({
    page
  }) => {
    // Same staleness setup; in lazy mode ipyflow wires hover handlers that
    // light up a cell's waiter / ready-maker links (ui/dom.ts).
    await openIpyflowNotebook(page, ['x = 1', 'y = x + 1', 'z = y + 1']);
    for (let i = 0; i < 3; i++) {
      await page.notebook.runCell(i);
    }
    await waitForEdge(page, 0, 1);
    await waitForEdge(page, 1, 2);

    await setCellSource(page, 0, 'x = 2');
    expect(await cellSource(page, 0)).toBe('x = 2');
    await page.notebook.runCell(0);
    await waitForCellClass(page, 2, 'waiting-cell');

    const linkedCount = () =>
      page.evaluate(
        () =>
          document.querySelectorAll('.linked-waiting, .linked-ready-maker')
            .length
      );

    expect(await linkedCount()).toBe(0);

    // Hover the waiting cell's input collapser: its linked (ready-maker) cell
    // should light up. Move the mouse away afterwards and the highlight clears.
    const waitingCell = await cellLocator(page, 2);
    await waitingCell.locator('.jp-InputCollapser').first().hover();
    await expect
      .poll(() => linkedCount(), {
        timeout: 15_000,
        message: 'hovering the stale cell highlighted no linked cells'
      })
      .toBeGreaterThan(0);

    await page.mouse.move(0, 0);
    await expect
      .poll(() => linkedCount(), {
        timeout: 15_000,
        message: 'link highlight did not clear after mouse-out'
      })
      .toBe(0);

    await settleAutosave(page);
  });
});
