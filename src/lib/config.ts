// Engine configuration: a single engine under test.
export interface EngineConfig {
  name: string;
  base_url: string;
  model: string;
  timeout: number;
  max_concurrent: number;
}

// Judge configuration: an optional model used for quality scoring.
export interface JudgeConfig {
  name: string;
  base_url: string;
  model: string;
  timeout: number;
}

import type { Task } from "./corpus/tasks.js";

// Top-level benchmark configuration.
export interface BenchmarkConfig {
  engines: EngineConfig[];
  judges: JudgeConfig[];
  tasks: Task[];
  task: string | null;
  max_concurrent: number;
  timeout: number;
  format: string;
  output: string | null;
  trials: number;
}

// Centralized default values shared by the dashboard.
export const DEFAULTS = {
  engine_base_url: "http://localhost:11434",
  engine_model: "llama3",
  judge_base_url: "http://localhost:11434",
  judge_model: "llama3",
  timeout: 60.0,
  max_concurrent: 1,
  format: "json",
  tasks: undefined,
  trials: 3,
} as const;
