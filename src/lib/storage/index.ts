// High-level storage access for results, engines, judges, models and corpus.

import type { EngineConfig, JudgeConfig } from "../config.js";
import type { Row } from "../results.js";
import type { Task, Corpus } from "../corpus/tasks.js";
import { buildDefaultCorpus } from "../corpus/tasks.js";
import * as db from "./db.js";

export type { Corpus } from "../corpus/tasks.js";

// `put` stores a single `{ rows }` record; `getAll` returns the array of
// records, so unwrap the envelope before returning the payload.
function unwrapRows(records: unknown[]): Row[] {
  const rows = (records as Array<{ rows: Row[] }> | null)?.flatMap(
    (r) => r.rows,
  );
  return rows ?? [];
}
function unwrapEngines(records: unknown[]): EngineConfig[] {
  const engines = (
    records as Array<{ engines: EngineConfig[] }> | null
  )?.flatMap((r) => r.engines);
  return engines ?? [];
}
function unwrapJudges(records: unknown[]): JudgeConfig[] {
  const judges = (records as Array<{ judges: JudgeConfig[] }> | null)?.flatMap(
    (r) => r.judges,
  );
  return judges ?? [];
}
function unwrapModels(
  records: unknown[],
): Array<{ engine: string; model: string; list: string[] }> {
  const models = (
    records as Array<{
      models: Array<{ engine: string; model: string; list: string[] }>;
    }> | null
  )?.flatMap((r) => r.models);
  return models ?? [];
}

export async function saveRows(rows: Row[]): Promise<void> {
  await db.put("rows", 0, { rows });
}

export async function loadRows(): Promise<Row[]> {
  return unwrapRows(await db.getAll("rows"));
}

export async function clearRows(): Promise<void> {
  const rows = await loadRows();
  if (rows.length) {
    await saveRows([]);
  }
}

export async function saveEngines(engines: EngineConfig[]): Promise<void> {
  await db.put("engines", 0, { engines });
}

export async function loadEngines(): Promise<EngineConfig[]> {
  return unwrapEngines(await db.getAll("engines"));
}

export async function saveJudges(judges: JudgeConfig[]): Promise<void> {
  await db.put("judges", 0, { judges });
}

export async function loadJudges(): Promise<JudgeConfig[]> {
  return unwrapJudges(await db.getAll("judges"));
}

export async function saveModels(
  models: Array<{ engine: string; model: string; list: string[] }>,
): Promise<void> {
  await db.put("models", 0, { models });
}

export async function loadModels(): Promise<
  Array<{ engine: string; model: string; list: string[] }>
> {
  return unwrapModels(await db.getAll("models"));
}

export async function saveTasks(tasks: Task[]): Promise<void> {
  await db.put("tasks", 0, tasks);
}

export async function loadTasks(): Promise<Task[]> {
  const stored = await db.get("tasks", 0);
  if (stored) {
    return stored as Task[];
  }
  return [];
}

export async function saveCorpus(corpus: Corpus): Promise<void> {
  await db.put("corpus", 0, corpus);
}

export async function loadCorpus(): Promise<Corpus> {
  const stored = await db.get("corpus", 0);
  if (stored) {
    return stored as Corpus;
  }
  return { tasks: buildDefaultCorpus() };
}

// Scalar task parameters (trials, max_concurrent, timeout). Stored as a single
// object under the `params` store so all three round-trip together on load.
export interface Params {
  trials: number;
  max_concurrent: number;
  timeout: number;
}

export async function saveParams(params: Params): Promise<void> {
  await db.put("params", 0, params);
}

export async function loadParams(): Promise<Params> {
  const stored = await db.get("params", 0);
  if (stored) {
    return stored as Params;
  }
  return { trials: 3, max_concurrent: 1, timeout: 60 };
}

// --- JSON export / import (optional) ---------------------------------------
// Serializes rows + config to a plain, JSON-serializable snapshot and
// restores it. Used for downloading/uploading benchmark state.

export interface StorageData {
  rows: Row[];
  engines: EngineConfig[];
  judges: JudgeConfig[];
  models: Array<{ engine: string; model: string; list: string[] }>;
  corpus: Corpus;
}

export async function exportData(): Promise<StorageData> {
  return {
    rows: await loadRows(),
    engines: await loadEngines(),
    judges: await loadJudges(),
    models: await loadModels(),
    corpus: await loadCorpus(),
  };
}

export async function importData(data: StorageData): Promise<void> {
  await Promise.all([
    saveRows(data.rows),
    saveEngines(data.engines),
    saveJudges(data.judges),
    saveModels(data.models),
    saveCorpus(data.corpus),
  ]);
}
