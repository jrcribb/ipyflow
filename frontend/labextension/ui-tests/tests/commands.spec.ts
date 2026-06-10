import { expect, test } from '@jupyterlab/galata';

import {
  attachNotebookDumpOnFailure,
  cellOutputText,
  cellSource,
  enableReactiveMode,
  openIpyflowNotebook,
  setCellSource,
  settleAutosave,
  waitForEdge
} from './helpers';

/**
 * ipyflow command-layer behaviors: the "Alt Mode Execute" command palette entry,
 * and the run-and-advance bookkeeping the run-cell patch does in batch-reactive
 * mode (insert a cell below when running the last cell; otherwise advance).
 */
test.describe('ipyflow commands', () => {
  attachNotebookDumpOnFailure(test);

  test.beforeEach(() => {
    test.setTimeout(120_000);
  });

  test('the Alt Mode Execute command runs the active cell forward closure', async ({
    page
  }) => {
    await openIpyflowNotebook(page, ['x = 1', 'print(x)']);
    await page.notebook.runCell(0, true);
    await page.notebook.runCell(1, true);
    await waitForEdge(page, 0, 1);
    expect(await cellOutputText(page, 1)).toContain('1');

    // The command exists with its palette label (this is what `palette.addItem`
    // surfaces in the command palette under the 'execution' category).
    const command = await page.evaluate(() => {
      const app = (window as any).jupyterapp;
      return {
        registered: app.commands.hasCommand('alt-mode-execute'),
        label: app.commands.label('alt-mode-execute')
      };
    });
    expect(command.registered).toBe(true);
    expect(command.label).toBe('Alt Mode Execute');

    // Change the parent, make it the active cell, and invoke the command the way
    // the palette entry does. In the default lazy + batch config it runs the
    // active cell's forward closure (cell0 -> cell1), so the dependent prints the
    // new value.
    await setCellSource(page, 0, 'x = 2');
    expect(await cellSource(page, 0)).toBe('x = 2');
    await page.notebook.selectCells(0);
    await page.evaluate(() =>
      (window as any).jupyterapp.commands.execute('alt-mode-execute')
    );

    await expect
      .poll(() => cellOutputText(page, 1), {
        timeout: 30_000,
        message: 'Alt Mode Execute did not run the forward closure'
      })
      .toContain('2');

    await settleAutosave(page);
  });

  test('run-and-advance inserts below the last cell in batch reactive', async ({
    page
  }) => {
    await openIpyflowNotebook(page, ['x = 1', 'print(x)']);
    await page.notebook.runCell(0, true);
    await page.notebook.runCell(1, true);
    await waitForEdge(page, 0, 1);
    await enableReactiveMode(page);

    const cellCount = () =>
      page.evaluate(
        () => (window as any).ipyflow.notebook.model.sharedModel.cells.length
      );
    const activeIndex = () =>
      page.evaluate(() => (window as any).ipyflow.notebook.activeCellIndex);

    expect(await cellCount()).toBe(2);

    // Run-and-advance (Shift+Enter) on the LAST cell: ipyflow inserts a fresh
    // cell below (so you can keep typing), growing the notebook to 3.
    await page.notebook.selectCells(1);
    await page.keyboard.press('Shift+Enter');
    await expect
      .poll(() => cellCount(), {
        timeout: 30_000,
        message: 'run-and-advance on the last cell did not insert a cell below'
      })
      .toBe(3);

    // Run-and-advance on a non-last cell just moves the cursor down; no insert.
    await page.notebook.selectCells(0);
    await page.keyboard.press('Shift+Enter');
    await expect
      .poll(() => activeIndex(), {
        timeout: 30_000,
        message: 'run-and-advance on a middle cell did not advance the cursor'
      })
      .toBe(1);
    expect(await cellCount()).toBe(3);

    await settleAutosave(page);
  });
});
