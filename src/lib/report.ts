// Report generation: serialize rows to JSON/CSV and print a summary.
//
// Mirrors `local_llm_benchmark/report.py`. Keeps the columns required by the
// spec: engine, model, judge, task_id, category, ttft_s, tok_per_s,
// iters_per_s, quality_passed, quality_deterministic, quality_judge,
// quality_note. Both JSON and CSV outputs include a `judge` field/column.

import { mkdirSync, writeFileSync } from "node:fs";
import type { Row } from "./results.js";
import { CSV_COLUMNS } from "./results.js";

// Export a Row as a plain, ordered object for JSON/CSV serialization.
export function rowToObject(row: Row): Row {
  return {
    engine: row.engine,
    model: row.model,
    judge: row.judge,
    task_id: row.task_id,
    category: row.category,
    prompt: row.prompt,
    expected: row.expected,
    output: row.output,
    ttft_s: row.ttft_s,
    tok_per_s: row.tok_per_s,
    iters_per_s: row.iters_per_s,
    quality_passed: row.quality_passed,
    quality_deterministic: row.quality_deterministic,
    quality_judge: row.quality_judge,
    quality_note: row.quality_note,
  };
}

function targetFor(path: string, ext: string): string {
  return path.endsWith(ext) ? path : `${path}${ext}`;
}

export function writeJSON(rows: Row[], path: string): void {
  const file = targetFor(path, ".json");
  mkdirSync(file.replace(/[/\\][^/\\]*$/, ""), { recursive: true });
  const text = JSON.stringify(rows.map(rowToObject), null, 2);
  writeFileSync(file, `${text}\n`, "utf-8");
}

export function writeCSV(rows: Row[], path: string): void {
  const file = targetFor(path, ".csv");
  mkdirSync(file.replace(/[/\\][^/\\]*$/, ""), { recursive: true });
  const header = CSV_COLUMNS.join(",");
  const serialized = rows.map((row) => rowToObject(row));
  const lines = serialized.map((row) =>
    CSV_COLUMNS.map((col) =>
      escapeCell(String((row as unknown as Record<string, unknown>)[col])),
    ),
  );
  writeFileSync(file, `${[header, ...lines].join("\n")}\n`, "utf-8");
}

export function writeReport(rows: Row[], path: string, fmt = "json"): void {
  if (fmt === "csv") {
    writeCSV(rows, path);
  } else {
    writeJSON(rows, path);
  }
}

export function printSummary(rows: Row[]): string {
  const list = [...rows];
  if (list.length === 0) {
    const message = "No results to summarize.";
    console.log(message);
    return message;
  }

  const engines = sortedKeys(list, "engine");
  const models = sortedKeys(list, "model");
  const judges = sortedKeys(
    list.filter((row) => row.judge),
    "judge",
  );
  const categories = sortedKeys(list, "category");

  const passed = list.filter((row) => row.quality_passed).length;
  const deterministic = list.filter((row) => row.quality_deterministic).length;

  const lines = [
    "Benchmark summary",
    "=".repeat(60),
    `engines:      ${engines}`,
    `models:       ${models}`,
    `judges:       ${judges || "none"}`,
    `categories:   ${categories}`,
    `rows:         ${list.length}`,
    `quality_passed:   ${passed}/${list.length}`,
    `deterministic:    ${deterministic}/${list.length}`,
    "",
    "Per-engine throughput (tok/s):",
  ];
  for (const engine of engines) {
    const rowsForEngine = list.filter((row) => row.engine === engine);
    if (rowsForEngine.length) {
      const best = Math.max(...rowsForEngine.map((row) => row.tok_per_s));
      const worst = Math.min(...rowsForEngine.map((row) => row.tok_per_s));
      lines.push(
        `  ${engine}: ${worst.toFixed(1)} .. ${best.toFixed(1)} tok/s`,
      );
    }
  }
  return lines.join("\n");
}

function sortedKeys(rows: Row[], key: keyof Row): string {
  const values = [...new Set(rows.map((row) => row[key]))].sort((a, b) =>
    String(a).localeCompare(String(b)),
  );
  return values.join(", ");
}

// Quote strings that need it (matches Python's csv module quoting for notes).
function escapeCell(value: string): string {
  if (value.includes(",") || value.includes('"') || value.includes("\n")) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}
