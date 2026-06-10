import { expect, test } from '@jupyterlab/galata';

import {
  attachNotebookDumpOnFailure,
  cellModelId,
  cellSource,
  execCount,
  openIpyflowNotebook,
  pressOnCell,
  readyAndWaitingCells,
  setCellSource,
  settleAutosave,
  waitForEdge
} from './helpers';

/**
 * End-to-end coverage of ipyflow's notebook keybindings (commands/commands.ts):
 *
 *   Accel J / Accel ArrowDown      -> execute-forward-slice
 *   Accel K / Accel ArrowUp        -> execute-backward-slice
 *   Ctrl/Accel Shift Enter         -> alt-mode-execute
 *   Space (command mode)           -> execute-stale (run ready cells)
 *
 * These commands run cells via ipyflow's own machinery (CodeCell.execute,
 * outside JupyterLab's run-cell path), so -- as in the reactive test -- we
 * trigger them with real key presses and poll execution counts for the effect
 * rather than relying on Galata's waitForRun.
 *
 * The fixture is a linear chain plus one independent cell:
 *
 *   cell0:  x = 1
 *   cell1:  y = x + 1     (depends on cell0)
 *   cell2:  z = y + 1     (depends on cell1)
 *   cell3:  w = 10        (independent)
 *
 * which lets each command assert a precise set of cells ran (and that the
 * others did not). 'Accel' resolves to Cmd on macOS and Ctrl on Linux; Lumino's
 * keybinding layer does the same per-platform detection, so we press the
 * matching modifier via Playwright's 'ControlOrMeta'.
 */

const CHAIN = ['x = 1', 'y = x + 1', 'z = y + 1', 'w = 10'];

/**
 * Open the 4-cell fixture, run each cell once, and await the dependency graph.
 *
 * Cells are run via `runCell` (the *patched* run path) rather than
 * `page.notebook.run()`: only a patched run requests a schedule recompute, which
 * is what populates the frontend store's dependency graph that these commands
 * traverse. In the default lazy mode, `runCell`'s waitForRun resolves normally
 * (the out-of-band execution caveat only applies to reactive runs).
 */
async function openChainAndRun(page: any): Promise<void> {
  await openIpyflowNotebook(page, CHAIN);
  for (let i = 0; i < CHAIN.length; i++) {
    await page.notebook.runCell(i);
  }
  await waitForEdge(page, 0, 1);
  await waitForEdge(page, 1, 2);
}

/** Snapshot the execution counts of all cells in the chain. */
async function counts(page: any): Promise<Array<number | null>> {
  return Promise.all(CHAIN.map((_, i) => execCount(page, i)));
}

/**
 * Press `keys` on `cellIndex`, then assert exactly the cells in `expectRan`
 * re-executed (execution count increased) and all others did not. Polls for the
 * expected bumps, then -- since unrelated cells are never submitted in lazy
 * mode -- checks the rest stayed put.
 */
async function expectKeyRuns(
  page: any,
  cellIndex: number,
  keys: string,
  expectRan: number[]
): Promise<void> {
  const before = await counts(page);
  await pressOnCell(page, cellIndex, keys);

  await expect
    .poll(
      async () => {
        const now = await counts(page);
        return expectRan.every((i) => (now[i] ?? 0) > (before[i] ?? 0));
      },
      {
        timeout: 30_000,
        message: `pressing ${keys} on cell ${cellIndex} did not run cells ${expectRan}`
      }
    )
    .toBe(true);

  const after = await counts(page);
  CHAIN.forEach((_, i) => {
    if (!expectRan.includes(i)) {
      expect(after[i], `cell ${i} should not have re-executed`).toBe(before[i]);
    }
  });

  await settleAutosave(page);
}

test.describe('ipyflow keybindings', () => {
  attachNotebookDumpOnFailure(test);

  test.beforeEach(async ({ page }) => {
    test.setTimeout(120_000);
  });

  test('Accel+J runs the forward slice (cell + descendants)', async ({
    page
  }) => {
    await openChainAndRun(page);
    // Forward slice from cell1 = {cell1, cell2}; cell0 and cell3 untouched.
    await expectKeyRuns(page, 1, 'ControlOrMeta+j', [1, 2]);
  });

  test('Accel+ArrowDown also runs the forward slice', async ({ page }) => {
    await openChainAndRun(page);
    await expectKeyRuns(page, 1, 'ControlOrMeta+ArrowDown', [1, 2]);
  });

  test('Accel+K runs the backward slice (cell + ancestors)', async ({
    page
  }) => {
    await openChainAndRun(page);
    // Backward slice from cell2 = {cell0, cell1, cell2}; cell3 untouched.
    await expectKeyRuns(page, 2, 'ControlOrMeta+k', [0, 1, 2]);
  });

  test('Accel+ArrowUp also runs the backward slice', async ({ page }) => {
    await openChainAndRun(page);
    await expectKeyRuns(page, 2, 'ControlOrMeta+ArrowUp', [0, 1, 2]);
  });

  test('Ctrl+Shift+Enter (alt-mode-execute) runs the forward closure', async ({
    page
  }) => {
    await openChainAndRun(page);
    // In the default lazy + batch reactivity config, alt-mode-execute from
    // cell0 runs cell0 and everything downstream of it: {cell0, cell1, cell2}.
    await expectKeyRuns(page, 0, 'Control+Shift+Enter', [0, 1, 2]);
  });

  test('Accel+Shift+Enter (alt-mode-execute) runs the forward closure', async ({
    page
  }) => {
    await openChainAndRun(page);
    await expectKeyRuns(page, 0, 'ControlOrMeta+Shift+Enter', [0, 1, 2]);
  });

  test('Space runs the ready cells (execute-stale)', async ({ page }) => {
    await openChainAndRun(page);

    // Re-run cell0 with a new value; cell1 (and transitively cell2) go stale,
    // becoming ready/waiting without being executed. Edit via the model
    // (setCellSource) -- galata's setCell can append in the windowed notebook.
    await setCellSource(page, 0, 'x = 100');
    expect(await cellSource(page, 0)).toBe('x = 100');
    await page.notebook.runCell(0);

    const child1 = await cellModelId(page, 1);
    await expect
      .poll(() => readyAndWaitingCells(page), {
        timeout: 30_000,
        message: 'cell1 never became ready after editing its parent'
      })
      .toContain(child1);

    // Space in command mode runs the ready set (cell1) and its batch closure
    // (cell2). cell0 was just executed (not ready) and cell3 is independent.
    await expectKeyRuns(page, 1, 'Space', [1, 2]);
  });
});
