import { expect, test } from '@jupyterlab/galata';

import {
  attachNotebookDumpOnFailure,
  buildCells,
  cellOutputText,
  setCellSource,
  settleAutosave
} from './helpers';

/**
 * The extension activates for every notebook, but it must stay out of the way on
 * non-ipyflow kernels: the run-cell patch falls back to vanilla execution and no
 * ipyflow comm is established (runCellPatch.ts / connect.ts).
 */
test.describe('ipyflow on a non-ipyflow kernel', () => {
  attachNotebookDumpOnFailure(test);

  test('a python3 notebook runs normally with no ipyflow comm or decorations', async ({
    page
  }) => {
    test.setTimeout(120_000);

    // A vanilla python3 kernel -- do NOT wait for the ipyflow comm (there is no
    // ipyflow comm target on this kernel, so it never establishes).
    await page.notebook.createNew(undefined, { kernel: 'python3' });
    await buildCells(page, ['x = 1', 'print(x + 1)']);

    await page.notebook.runCell(0, true);
    await page.notebook.runCell(1, true);

    // The cells executed via the normal Jupyter path.
    await expect
      .poll(() => cellOutputText(page, 1), {
        timeout: 30_000,
        message: 'python3 cell did not execute normally'
      })
      .toContain('2');

    // No ipyflow comm was established for this kernel...
    expect(
      await page.evaluate(
        () => (window as any).ipyflow?.isIpyflowCommConnected ?? false
      )
    ).toBe(false);

    // ...and editing + re-running a parent does NOT produce ipyflow staleness
    // decorations (there is no dataflow tracking here).
    await setCellSource(page, 0, 'x = 99');
    await page.notebook.runCell(0, true);
    await settleAutosave(page);
    expect(
      await page.evaluate(
        () =>
          document.querySelectorAll(
            '.ready-cell, .waiting-cell, .ipyflow-slice-execute'
          ).length
      )
    ).toBe(0);

    await settleAutosave(page);
  });
});
