// High-level storage access for results, engines, judges, models and corpus.

import type { EngineConfig, JudgeConfig } from "../config.js";
import type { Row } from "../results.js";
import type { Task } from "../corpus/tasks.js";
import { buildDefaultCorpus } from "../corpus/tasks.js";
import * as db from "./db.js";

export interface Corpus {
  tasks: Task[];
}

export async function saveRows(rows: Row[]): Promise<void> {
  await db.put("rows", 0, { rows });
}

export async function loadRows(): Promise<Row[]> {
  const rows = await db.getAll("rows");
  return rows as Row[];
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
  const engines = await db.getAll("engines");
  return engines as EngineConfig[];
}

export async function saveJudges(judges: JudgeConfig[]): Promise<void> {
  await db.put("judges", 0, { judges });
}

export async function loadJudges(): Promise<JudgeConfig[]> {
  const judges = await db.getAll("judges");
  return judges as JudgeConfig[];
}

export async function saveModels(
  models: Array<{ engine: string; model: string; list: string[] }>,
): Promise<void> {
  await db.put("models", 0, { models });
}

export async function loadModels(): Promise<
  Array<{ engine: string; model: string; list: string[] }>
> {
  const models = await db.getAll("models");
  return models as Array<{ engine: string; model: string; list: string[] }>;
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
