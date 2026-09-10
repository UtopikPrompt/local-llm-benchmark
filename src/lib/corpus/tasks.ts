// Task definition: a single prompt the benchmark asks an engine to answer.
// `category` mirrors the Python `TaskCategory` enum; the default corpus covers
// all four: doc, code, qa, math.
//
// This module is the single canonical source for the task/judge/category types.
// Other modules must import from here (e.g. `import type { Task } from '../corpus/tasks.js'`).

export type Category = "doc" | "code" | "qa" | "math";

export const CATEGORIES: readonly Category[] = ["doc", "code", "qa", "math"];

export type TaskValidator = (solution: string) => boolean;

export interface Task {
  id: string;
  category: Category;
  prompt: string;
  system: string | null;
  expected: string | null;
  validate: TaskValidator | null;
}

// A Judge scores answers. `score` runs the judge engine over the answer and
// returns whether it agreed plus a human-readable reason.
export interface Judge {
  name: string;
  score(task: Task, answer: string): Promise<{ agreed: boolean; note: string }>;
}

// Deterministic validators for the math tasks. The rest of the corpus relies
// on substring matching in the runner (via ``expected``).
export function validateSolution(solution: string): boolean {
  const cleaned = solution.trim().toLowerCase().replace(/\s+/g, " ");
  return "x = 5" in cleaned || "x=5" in cleaned || "5" in cleaned;
}

export function validateArea(area: string): boolean {
  const cleaned = area.trim().replace(/\s+/g, " ");
  if (!/^\d*\.?\d+$/.test(cleaned)) {
    return false;
  }
  const value = Number(cleaned);
  return Math.abs(value - 153.938) / 153.938 < 0.02;
}

const _VALIDATORS: Record<Task["id"], TaskValidator> = {
  "math-solve-2x-5-15": validateSolution,
  "math-area-circle-r7": validateArea,
};

/**
 * Build the default corpus (8 tasks). A fresh copy is returned each call so
 * callers can mutate it without affecting the shared default.
 */
export function buildDefaultCorpus(): Task[] {
  const tasks: Task[] = [
    {
      id: "doc-rest-api",
      category: "doc",
      prompt:
        "A brief overview of the REST API: list resources by GET, read by GET /{id}, update with PUT /{id}, delete with DELETE /{id}. All endpoints return JSON and accept an Authorization header for protected resources.",
      expected: "GET",
    },
    {
      id: "doc-password-reset",
      category: "doc",
      prompt:
        "How to reset your password: visit the password-reset page, enter your email, follow the link in the confirmation email, and choose a new password that is at least 12 characters long.",
      expected: "password-reset",
    },
    {
      id: "code-sort-dict-by-value",
      category: "code",
      prompt: "Sort a Python dictionary by its values in ascending order.",
      expected: "sorted",
    },
    {
      id: "code-httpx-get-timeout",
      category: "code",
      prompt: "Fetch a URL using httpx with a per-request timeout.",
      expected: "httpx",
    },
    {
      id: "qa-first-iphone-year",
      category: "qa",
      prompt: "What year was the first iPhone released?",
      expected: "2007",
    },
    {
      id: "qa-train-distance",
      category: "qa",
      prompt: "How far do the rails of a standard train track extend?",
      expected: "1132",
    },
    {
      id: "math-solve-2x-5-15",
      category: "math",
      prompt: "Solve the equation 2x + 5 = 15 for x.",
      expected: "x = 5",
    },
    {
      id: "math-area-circle-r7",
      category: "math",
      prompt: "What is the area of a circle with radius 7? Use pi = 3.14159.",
      expected: "153.938",
    },
  ];
  tasks.forEach((task) => {
    const validator = _VALIDATORS[task.id];
    if (validator) {
      task.validate = validator;
    }
  });
  return tasks;
}

export const defaultTasks = buildDefaultCorpus();
