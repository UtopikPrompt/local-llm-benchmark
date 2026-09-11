// Task / Judge / TaskValidator / Corpus types live once in corpus/tasks.ts
// (the canonical home). This module re-exports them so the runner, storage and
// UI can import from './tasks.js' without a duplicate definition.

export type { Task, TaskValidator, Judge, Corpus } from "./corpus/tasks.js";
