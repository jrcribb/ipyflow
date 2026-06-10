import { expect, test } from '@jupyterlab/galata';

import {
  attachNotebookDumpOnFailure,
  cellLocator,
  cellModelId,
  cellSource,
  execCount,
  openIpyflowNotebook,
  readyAndWaitingCells,
  setCellSource,
  settleAutosave,
  waitForEdge,
  waitForExecMode
} from './helpers';

/**
 * End-to-end tests that drive a real JupyterLab + ipyflow kernel and assert on
 * the extension's behavior: comm establishment, dependency-aware cell
 * decoration, and reactive re-execution. The session store is exposed on
 * `window.ipyflow` (state/registry.ts) and read here via page.evaluate; shared
 * plumbing lives in ./helpers.
 */
test.describe('ipyflow extension', () => {
  attachNotebookDumpOnFailure(test);

  test('establishes the ipyflow comm on the ipyflow kernel', async ({
    page
  }) => {
    await openIpyflowNotebook(page, ['x = 1', 'y = x + 1']);
    expect(
      await page.evaluate(() => (window as any).ipyflow?.isIpyflowCommConnected)
    ).toBe(true);
  });

  test('flags a dependent cell as ready after its parent is re-run', async ({
    page
  }) => {
    await openIpyflowNotebook(page, ['x = 1', 'y = x + 1']);
    await page.notebook.run(); // run both; graph is now clean

    // Re-run cell 0 with a new value; cell 1 was computed from the old x. Edit
    // via the model (setCellSource) rather than galata's setCell, which retypes
    // into the editor and intermittently *appends* in ipyflow's windowed
    // notebook (yielding a corrupt 'x = 2x = 1'); the guard asserts a clean edit.
    await setCellSource(page, 0, 'x = 2');
    expect(await cellSource(page, 0)).toBe('x = 2');
    await page.notebook.runCell(0);

    const childId = await cellModelId(page, 1);
    expect(childId).toBeTruthy();

    // The dependent cell should be reported ready/waiting by the store ...
    await expect
      .poll(() => readyAndWaitingCells(page), {
        timeout: 30_000,
        message: 'dependent cell never became ready'
      })
      .toContain(childId);

    // ... and carry an ipyflow decoration class in the DOM.
    await expect(await cellLocator(page, 1)).toHaveClass(
      /(ready-cell|ready-making-cell|waiting-cell)/,
      { timeout: 30_000 }
    );

    await settleAutosave(page);
  });

  test('reactively re-executes a dependent cell', async ({ page }) => {
    test.setTimeout(120_000);
    await openIpyflowNotebook(page, [
      'x = 1',
      'y = x + 1',
      '%flow mode reactive'
    ]);
    // Run each cell through the patched run command (Shift+Enter) so ipyflow
    // computes the dependency graph; the last cell switches to reactive mode.
    await page.notebook.runCell(0);
    await page.notebook.runCell(1);
    await page.notebook.runCell(2);

    // Wait until reactive mode is active and the cell0 -> cell1 edge is known,
    // so the reactive run below has a populated graph to traverse.
    await waitForExecMode(page, 'reactive');
    await waitForEdge(page, 0, 1);

    const before = await execCount(page, 1);

    // Re-run only cell 0 in place via the keyboard; reactive mode should also
    // re-execute its dependent (cell 1), bumping cell 1's execution count
    // without running it directly. We press the key ourselves rather than using
    // page.notebook.runCell, whose waitForRun does not understand ipyflow's
    // reactive execution (which runs cells outside galata's normal run path).
    await page.notebook.selectCells(0);
    await page.keyboard.press('Control+Enter');

    await expect
      .poll(() => execCount(page, 1), {
        timeout: 30_000,
        message: 'dependent cell was not reactively re-executed'
      })
      .toBeGreaterThan(before as number);

    await settleAutosave(page);
  });
});
