import { expect, test } from '@jupyterlab/galata';

import {
  attachNotebookDumpOnFailure,
  cellLocator,
  cellModelId,
  cellOutputText,
  cellSource,
  enableReactiveMode,
  openIpyflowNotebook,
  readyAndWaitingCells,
  restartKernel,
  setCellSource,
  settleAutosave,
  waitForEdge
} from './helpers';

/**
 * End-to-end tests covering ipyflow's behavior across a kernel restart.
 *
 * ipyflow persists its dependency graph in the notebook model's `ipyflow`
 * metadata (comm/schedule.ts writes `cell_parents` / `cell_children`), and on
 * (re)connect it replays that graph to the kernel via the comm open payload
 * (comm/connect.ts -> flow.initialize). So after a restart -- when the kernel
 * has no execution history of its own -- the dependency edges are still known,
 * and running a parent cell flags its dependents as stale/ready.
 *
 * Two things do NOT survive a restart, which shapes how these tests assert:
 *   - the exec mode resets to the default (lazy), so the reactive tests re-issue
 *     `%flow mode reactive` after restarting; and
 *   - the kernel's execution counter resets, so a reactive re-execution cannot
 *     be detected by a *higher* execution count. Instead the dependent cell
 *     prints a value derived from its parent, and we assert the printed output
 *     changes -- which also confirms the new value actually propagated.
 *
 * The cells are run via `runCell` (the patched run path) rather than
 * `page.notebook.run()` so the frontend dependency graph (and thus the persisted
 * metadata) is actually populated before the restart.
 */
test.describe('ipyflow across kernel restart', () => {
  attachNotebookDumpOnFailure(test);

  test.beforeEach(() => {
    test.setTimeout(120_000);
  });

  /** Open [x, print(x)], run both via patched runs, await the edge + autosave. */
  async function openAndRunPrintChain(page: any): Promise<void> {
    await openIpyflowNotebook(page, ['x = 1', 'print(x)']);
    await page.notebook.runCell(0);
    await page.notebook.runCell(1);
    await waitForEdge(page, 0, 1);
    await settleAutosave(page); // let the graph land in notebook metadata
  }

  test('persists the dependency graph across a kernel restart', async ({
    page
  }) => {
    await openAndRunPrintChain(page);

    await restartKernel(page);

    // The frontend graph (merged from the persisted metadata) still has the
    // edge after the restart...
    await waitForEdge(page, 0, 1);

    // ...and the kernel honors it: with a fresh kernel that never saw cell1
    // run, editing + running its parent must still flag cell1 as ready. That is
    // only possible because the cell0 -> cell1 edge was replayed from metadata.
    await setCellSource(page, 0, 'x = 2');
    expect(await cellSource(page, 0)).toBe('x = 2'); // guard against stale-edit append
    await page.notebook.runCell(0);

    const childId = await cellModelId(page, 1);
    expect(childId).toBeTruthy();

    await expect
      .poll(() => readyAndWaitingCells(page), {
        timeout: 30_000,
        message: 'dependent cell never became ready after restart'
      })
      .toContain(childId);

    await expect(await cellLocator(page, 1)).toHaveClass(
      /(ready-cell|ready-making-cell|waiting-cell)/,
      { timeout: 30_000 }
    );

    await settleAutosave(page);
  });

  test('reactively re-executes immediately after a kernel restart', async ({
    page
  }) => {
    await openAndRunPrintChain(page);
    expect(await cellOutputText(page, 1)).toContain('1');

    await restartKernel(page);

    // Re-enable reactive mode (lost on restart) and re-establish the graph, then
    // immediately drive a reactive run -- no artificial wait beyond what the
    // graph/comm genuinely need.
    await enableReactiveMode(page);
    await waitForEdge(page, 0, 1);

    // Change the parent's value and reactively run it; the dependent print cell
    // should reactively re-execute and emit the new value.
    await setCellSource(page, 0, 'x = 42');
    expect(await cellSource(page, 0)).toBe('x = 42'); // guard against stale-edit append
    await page.notebook.selectCells(0);
    await page.keyboard.press('Control+Enter');

    await expect
      .poll(() => cellOutputText(page, 1), {
        timeout: 30_000,
        message:
          'dependent cell did not reactively re-execute right after restart'
      })
      .toContain('42');

    await settleAutosave(page);
  });

  test('reactively re-executes after idling post-restart', async ({ page }) => {
    await openAndRunPrintChain(page);
    expect(await cellOutputText(page, 1)).toContain('1');

    await restartKernel(page);
    await enableReactiveMode(page);
    await waitForEdge(page, 0, 1);

    // Let the freshly restarted kernel sit idle for a few seconds before the
    // reactive run, to catch regressions where reactivity only works while the
    // post-restart state is still "warm".
    await page.waitForTimeout(5000);

    await setCellSource(page, 0, 'x = 99');
    expect(await cellSource(page, 0)).toBe('x = 99'); // guard against stale-edit append
    await page.notebook.selectCells(0);
    await page.keyboard.press('Control+Enter');

    await expect
      .poll(() => cellOutputText(page, 1), {
        timeout: 30_000,
        message:
          'dependent cell did not reactively re-execute after idling post-restart'
      })
      .toContain('99');

    await settleAutosave(page);
  });
});
