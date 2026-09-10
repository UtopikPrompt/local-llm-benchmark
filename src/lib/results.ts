// Row: one measurement per (engine, task) trial.
export interface Row {
  engine: string;
  model: string;
  judge: string;
  task_id: string;
  category: string;
  prompt: string;
  expected: string;
  output: string;
  ttft_s: number;
  tok_per_s: number;
  iters_per_s: number;
  quality_passed: boolean;
  quality_deterministic: boolean;
  quality_judge: boolean;
  quality_note: string;
}

// Ordered CSV columns for the exported report.
export const CSV_COLUMNS: readonly string[] = [
  "engine",
  "model",
  "judge",
  "task_id",
  "category",
  "ttft_s",
  "tok_per_s",
  "iters_per_s",
  "quality_passed",
  "quality_deterministic",
  "quality_judge",
  "quality_note",
];

export type Category = "doc" | "code" | "qa" | "math";

export const CATEGORIES: readonly Category[] = ["doc", "code", "qa", "math"];
