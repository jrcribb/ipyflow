import { expect, test } from '@jupyterlab/galata';

import {
  attachNotebookDumpOnFailure,
  cellModelId,
  cellOutputText,
  cellSource,
  enableReactiveMode,
  openIpyflowNotebook,
  readyAndWaitingCells,
  setCellSource,
  setFlowMode,
  settleAutosave,
  waitForEdge
} from './helpers';

/**
 * Execution-mode behaviors: how a reactive cascade handles an error mid-stream,
 * and that toggling between reactive and lazy actually changes whether
 * dependents auto-execute.
 *
 * Reactive runs happen outside Galata's run path, so effects are observed by
 * polling the dependent cells' printed output / ready state.
 */
test.describe('ipyflow execution modes', () => {
  attachNotebookDumpOnFailure(test);

  test.beforeEach(() => {
    test.setTimeout(120_000);
  });

  test('an error mid-cascade stops the downstream reactive re-execution', async ({
    page
  }) => {
    // cell1 assigns y (to a parent-derived value) and THEN raises, so if the
    // cascade wrongly continued, cell2 would print the new y (70). It must not.
    await openIpyflowNotebook(page, [
      'x = 1',
      'y = x * 10\nassert x < 5',
      'print(y)'
    ]);
    for (let i = 0; i < 3; i++) {
      await page.notebook.runCell(i);
    }
    await waitForEdge(page, 0, 1);
    await waitForEdge(page, 1, 2);
    expect(await cellOutputText(page, 2)).toContain('10');

    await enableReactiveMode(page);
    await waitForEdge(page, 0, 1);
    await waitForEdge(page, 1, 2);

    // x = 7 makes y = 70, then cell1's assert fails -> cascade must abort before
    // cell2 re-runs.
    await setCellSource(page, 0, 'x = 7');
    expect(await cellSource(page, 0)).toBe('x = 7');
    await page.notebook.selectCells(0);
    await page.keyboard.press('Control+Enter');

    // cell1 reactively re-ran and raised.
    await expect
      .poll(() => cellOutputText(page, 1), {
        timeout: 30_000,
        message: 'cell1 never reactively re-ran / raised'
      })
      .toContain('AssertionError');

    // cell2 must NOT have re-executed with the new value.
    await settleAutosave(page);
    expect(await cellOutputText(page, 2)).not.toContain('70');

    await settleAutosave(page);
  });

  test('switching from reactive back to lazy stops dependents from auto-running', async ({
    page
  }) => {
    await openIpyflowNotebook(page, ['x = 1', 'print(x)']);
    await page.notebook.runCell(0);
    await page.notebook.runCell(1);
    await waitForEdge(page, 0, 1);
    expect(await cellOutputText(page, 1)).toContain('1');

    // In reactive mode a parent re-run cascades to the dependent.
    await enableReactiveMode(page);
    await setCellSource(page, 0, 'x = 2');
    expect(await cellSource(page, 0)).toBe('x = 2');
    await page.notebook.selectCells(0);
    await page.keyboard.press('Control+Enter');
    await expect
      .poll(() => cellOutputText(page, 1), {
        timeout: 30_000,
        message: 'reactive cascade did not update the dependent'
      })
      .toContain('2');

    // Back to lazy: re-running the parent should now only FLAG the dependent
    // ready, not execute it -- its printed output stays at the previous value.
    await setFlowMode(page, 'lazy');
    await setCellSource(page, 0, 'x = 3');
    expect(await cellSource(page, 0)).toBe('x = 3');
    await page.notebook.runCell(0);

    const childId = await cellModelId(page, 1);
    await expect
      .poll(() => readyAndWaitingCells(page), {
        timeout: 30_000,
        message: 'dependent was not flagged ready in lazy mode'
      })
      .toContain(childId);

    // It did not auto-run, so its output is still the reactive-era value (2).
    expect(await cellOutputText(page, 1)).toContain('2');
    expect(await cellOutputText(page, 1)).not.toContain('3');

    await settleAutosave(page);
  });
});
