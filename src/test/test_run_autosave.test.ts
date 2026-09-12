// Integration test: mounts the real +page.svelte run page and verifies the
// debounced reactive autosave writes field edits to IndexedDB.
//
// This exercises the actual Svelte component (not just the storage layer),
// catching regressions in the reactive signature/dirty-flag logic.

import { describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render } from "@testing-library/svelte";
import type { RenderResult } from "@testing-library/svelte";
import RunPage from "../routes/run/+page.svelte";

import "fake-indexeddb/auto";

import {
  loadEngines,
  loadTasks,
  saveEngines,
  saveTasks,
} from "../lib/storage/index.js";

// The run page imports buildDefaultCorpus, which pulls in the full task corpus.
// We stub it so the component renders without a heavy corpus module.
vi.mock("../lib/corpus/tasks.js", () => ({
  buildDefaultCorpus: () => [
    { id: "task-a", category: "qa", prompt: "task-a" },
  ],
}));

describe("run page autosave (real component)", () => {
  it("persists an engine-name edit to IndexedDB after the debounce", async () => {
    render(RunPage);

    // Wait for onMount() to finish loading engines/tasks from the (fake) DB.
    await vi.waitFor(() => {
      expect(loadEngines()).resolves.toHaveLength(1);
    });

    // Edit the engine name field.
    const engineNameInput = document.querySelector<HTMLInputElement>(
      'input[placeholder="Ollama"]',
    );
    expect(engineNameInput).not.toBeNull();
    fireEvent.input(engineNameInput!, {
      target: { value: "MyCustomEngine99" },
    });

    // Wait for the 400ms debounce + the async persistConfig() to complete.
    await vi.waitFor(
      async () => {
        const engines = await saveEngines([]); // noop to flush
        expect(
          (await loadEngines()).some((e) => e.name === "MyCustomEngine99"),
        ).toBe(true);
      },
      { timeout: 4000 },
    );

    // Verify the value is actually stored.
    const engines = await loadEngines();
    expect(engines).toHaveLength(1);
    expect(engines[0].name).toBe("MyCustomEngine99");

    cleanup();
  });
});
