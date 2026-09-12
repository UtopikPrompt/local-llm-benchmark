import { describe, expect, it } from "vitest";
import "fake-indexeddb/auto";
// `fake-indexeddb/auto` installs the IndexedDB globals as a side-effect on
// import (once per test file). The `dbPromise` singleton in db.ts keeps writing
// to the same fake DB across tests, so a single full round-trip test avoids
// cross-test pollution.

import { put, get, getAll } from "../lib/storage/db.js";
import {
	saveEngines,
	loadEngines,
	saveJudges,
	loadJudges,
	saveModels,
	loadModels,
	saveTasks,
	loadTasks,
	saveRows,
	loadRows,
	saveCorpus,
	loadCorpus,
} from "../lib/storage/index.js";

describe("db.ts + storage/index.ts round-trip (fake-indexeddb)", () => {
	it("round-trips every store through db.ts and index.ts", async () => {
		const engines = [
			{ name: "ollama", base_url: "http://a", model: "m1" },
			{ name: "lmstudio", base_url: "http://b", model: "m2" },
		];
		const judges = [{ name: "judge1", base_url: "http://j", model: "jm" }];
		const models = [
			{ engine: "ollama", model: "m1", list: ["a", "b"] },
			{ engine: "lmstudio", model: "m2", list: ["c"] },
		];
		const tasks = [
			{ id: "1", category: "qa", prompt: "1", system: "s", expected: "e" },
			{ id: "2", category: "qa", prompt: "2" },
		];
		const rows = [
			{ prompt: "p1", response: "r1" },
			{ prompt: "p2", response: "r2" },
		];
		const corpus = { tasks: [{ id: "1", category: "qa", prompt: "1" }] };

		// Single write phase — every store keyed at 0 with its envelope.
		await Promise.all([
			saveEngines(engines),
			saveJudges(judges),
			saveModels(models),
			saveTasks(tasks),
			saveRows(rows),
			saveCorpus(corpus),
		]);

		expect(await loadEngines()).toEqual(engines);
		expect(await loadJudges()).toEqual(judges);
		expect(await loadModels()).toEqual(models);
		expect(await loadTasks()).toEqual(tasks);
		expect(await loadRows()).toEqual(rows);
		expect(await loadCorpus()).toEqual(corpus);

		// Raw db.ts envelope contract: single record per store.
		expect(await get("engines", 0)).toEqual({ engines });
		expect(await get("judges", 0)).toEqual({ judges });
		expect(await get("models", 0)).toEqual({ models });
		expect(await get("tasks", 0)).toEqual(tasks);
		expect(await get("rows", 0)).toEqual({ rows });
		expect(await get("corpus", 0)).toEqual(corpus);

		expect(await getAll("engines")).toHaveLength(1);
		expect(await getAll("tasks")).toHaveLength(1);
		expect(await getAll("rows")).toHaveLength(1);
		expect(await getAll("corpus")).toHaveLength(1);
	});
});
