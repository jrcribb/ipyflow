import { test } from '@jupyterlab/galata';

import {
  attachNotebookDumpOnFailure,
  openIpyflowNotebook,
  settleAutosave,
  waitForComm,
  waitForEdge
} from './helpers';

/**
 * ipyflow persists its dependency graph into the notebook's `ipyflow` metadata
 * and saves it to the .ipynb on disk. This exercises the disk round-trip: run a
 * chain, save, close the notebook, and reopen it -- which reloads the model from
 * the saved file and starts a fresh kernel -- then confirm the edge is restored
 * from disk without re-running anything.
 *
 * (We close + reopen rather than reloading the whole browser page: a mid-test
 * `page.reload()` desyncs Galata's fixtures. Reopening still recreates the model
 * from the .ipynb, which is what the persistence path depends on.)
 */
test.describe('ipyflow persistence', () => {
  attachNotebookDumpOnFailure(test);

  test('the dependency graph survives closing and reopening the notebook', async ({
    page
  }) => {
    test.setTimeout(120_000);

    const name = await openIpyflowNotebook(page, ['x = 1', 'y = x + 1']);
    await page.notebook.runCell(0, true);
    await page.notebook.runCell(1, true);
    await waitForEdge(page, 0, 1);

    // Flush the debounced graph-save and force the .ipynb to disk.
    await settleAutosave(page);
    await page.notebook.save();

    // Close (keeping the saved file) and reopen from disk.
    await page.notebook.close();
    await page.notebook.open(name);
    await waitForComm(page);

    // The edge is present purely from the persisted metadata -- nothing was
    // re-run after reopening.
    await waitForEdge(page, 0, 1);

    await settleAutosave(page);
  });
});
