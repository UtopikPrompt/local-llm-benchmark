// Shared UI helpers mirroring the domain model.
import type { Category } from "./corpus/tasks.js";
import type { EngineConfig } from "./config.js";
import type { Task } from "./tasks.js";
import { page } from "$app/stores";

export interface EngineModel {
  engine: string;
  model: string;
  list: string[];
}

export interface CorpusConfig {
  tasks: Task[];
}

export interface Filters {
  engine: string;
  model: string;
  category: string;
  quality: string;
  judge: string;
}

export const DEFAULT_FILTERS: Filters = {
  engine: "",
  model: "",
  category: "",
  quality: "",
  judge: "",
};

export const CATEGORIES: Category[] = ["doc", "code", "qa", "math"];

export function activeRoute(): string {
  return (page as unknown as { url: { pathname: string } }).url.pathname;
}
