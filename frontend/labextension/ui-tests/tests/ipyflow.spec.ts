import { expect, test } from '@jupyterlab/galata';

/**
 * End-to-end tests that drive a real JupyterLab + ipyflow kernel and assert on
 * the extension's behavior: comm establishment, dependency-aware cell
 * decoration, and reactive re-execution. The session store is exposed on
 * `window.ipyflow` (state/registry.ts) and read here via page.evaluate.
 */

/** Poll until the ipyflow comm has established (window.ipyflow is the store). */
async function waitForComm(page: any): Promise<void> {
  await expect
    .poll(
      () =>
        page.evaluate(
          () => (window as any).ipyflow?.isIpyflowCommConnected ?? false
        ),
      { timeout: 60_000, message: 'ipyflow comm never connected' }
    )
    .toBe(true);
}

/** Create a notebook on the ipyflow kernel, populate `cells`, await the comm. */
async function openIpyflowNotebook(page: any, cells: string[]): Promise<void> {
  await page.notebook.createNew(undefined, { kernel: 'ipyflow' });
  // Wait for the comm to establish on the fresh (empty) notebook BEFORE adding
  // cells. The establish handler flips the notebook into windowed-scrollbar
  // mode and re-renders; letting that happen concurrently with galata's cell
  // construction races and can hang addCell (the cell DOM shifts underneath it).
  await waitForComm(page);
  for (let i = 0; i < cells.length; i++) {
    if (i === 0) {
      await page.notebook.setCell(0, 'code', cells[0]);
    } else {
      await page.notebook.addCell('code', cells[i]);
    }
  }
}

const readyAndWaitingCells = (page: any): Promise<string[]> =>
  page.evaluate(() => {
    const s = (window as any).ipyflow;
    return s ? [...(s.readyCells ?? []), ...(s.waitingCells ?? [])] : [];
  });

const cellModelId = (page: any, index: number): Promise<string | undefined> =>
  page.evaluate(
    (i: number) => (window as any).ipyflow?.notebook?.widgets?.[i]?.model?.id,
    index
  );

async function cellLocator(page: any, index: number) {
  const nb = await page.notebook.getNotebookInPanelLocator();
  return nb.locator('.jp-Cell').nth(index);
}

/**
 * After each schedule, ipyflow persists its dependency graph via a 200ms-
 * debounced notebook save. Galata deletes each test's temp directory on
 * teardown, so a save that fires mid-teardown 500s ("File Save Error"). Let the
 * debounced save flush while the notebook still exists before the test ends.
 */
async function settleAutosave(page: any): Promise<void> {
  await page.waitForTimeout(1000);
}

test.describe('ipyflow extension', () => {
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

    // Re-run cell 0 with a new value; cell 1 was computed from the old x.
    await page.notebook.setCell(0, 'code', 'x = 2');
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
    await expect
      .poll(
        () =>
          page.evaluate(() => {
            const s = (window as any).ipyflow;
            const id0 = s?.notebook?.widgets?.[0]?.model?.id;
            const id1 = s?.notebook?.widgets?.[1]?.model?.id;
            return (
              s?.settings?.exec_mode === 'reactive' &&
              (s?.cellChildren?.[id0] ?? []).includes(id1)
            );
          }),
        { timeout: 30_000, message: 'reactive mode / dep graph not ready' }
      )
      .toBe(true);

    const execCount1 = (): Promise<number | null> =>
      page.evaluate(
        () => (window as any).ipyflow?.notebook?.widgets?.[1]?.model?.executionCount ?? null
      );
    const before = await execCount1();

    // Re-run only cell 0 in place via the keyboard; reactive mode should also
    // re-execute its dependent (cell 1), bumping cell 1's execution count
    // without running it directly. We press the key ourselves rather than using
    // page.notebook.runCell, whose waitForRun does not understand ipyflow's
    // reactive execution (which runs cells outside galata's normal run path).
    await page.notebook.selectCells(0);
    await page.keyboard.press('Control+Enter');

    await expect
      .poll(() => execCount1(), {
        timeout: 30_000,
        message: 'dependent cell was not reactively re-executed'
      })
      .toBeGreaterThan(before as number);

    await settleAutosave(page);
  });
});
