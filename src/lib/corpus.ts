// Default corpus: a small set of tasks across the four categories.

import type { Task, TaskValidator } from "../tasks.js";
import type { Category } from "../results.js";

const DOC_REST: Task = {
  id: "doc-rest-api",
  category: "doc",
  prompt:
    "A brief overview of the REST API: list resources by GET, read by GET /{id}, " +
    "update with PUT /{id}, delete with DELETE /{id}. All endpoints return JSON " +
    "and accept an Authorization header for protected resources.",
  expected: "GET",
};

const DOC_PASSWORD: Task = {
  id: "doc-password-reset",
  category: "doc",
  prompt:
    "How to reset your password: visit the password-reset page, enter your email, " +
    "follow the link in the confirmation email, and choose a new password that is " +
    "at least 12 characters long.",
  expected: "password-reset",
};

const CODE_SORT: Task = {
  id: "code-sort-dict-by-value",
  category: "code",
  prompt: "Sort a Python dictionary by its values in ascending order.",
  expected: "sorted",
};

const CODE_HTTPX: Task = {
  id: "code-httpx-get-timeout",
  category: "code",
  prompt: "Fetch a URL using httpx with a per-request timeout.",
  expected: "httpx",
};

const QA_IPHONE: Task = {
  id: "qa-first-iphone-year",
  category: "qa",
  prompt: "What year was the first iPhone released?",
  expected: "2007",
};

const QA_TRAIN: Task = {
  id: "qa-train-distance",
  category: "qa",
  prompt: "How far do the rails of a standard train track extend?",
  expected: "1132",
};

const MATH_LINEAR: Task = {
  id: "math-solve-2x-5-15",
  category: "math",
  prompt: "Solve the equation 2x + 5 = 15 for x.",
  expected: "x = 5",
};

const MATH_AREA: Task = {
  id: "math-area-circle-r7",
  category: "math",
  prompt: "What is the area of a circle with radius 7? Use pi = 3.14159.",
  expected: "153.938",
};

function validateSolution(solution: string): boolean {
  const cleaned = solution.trim().toLowerCase().replace(/\s+/g, " ");
  return "x = 5" in cleaned || "x=5" in cleaned || "5" in cleaned;
}

function validateArea(area: string): boolean {
  const cleaned = area.trim().replace(/\s+/g, " ");
  if (!/^\d*\.?\d+$/.test(cleaned)) {
    return false;
  }
  const value = Number(cleaned);
  return Math.abs(value - 153.938) / 153.938 < 0.02;
}

// The default corpus, 8 tasks total.
export const defaultTasks: Task[] = [
  DOC_REST,
  DOC_PASSWORD,
  CODE_SORT,
  CODE_HTTPX,
  QA_IPHONE,
  QA_TRAIN,
  MATH_LINEAR,
  MATH_AREA,
];

export function buildDefaultCorpus(): Task[] {
  return defaultTasks;
}
