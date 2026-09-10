// Engine registry: build concrete engines from configuration.

import { BenchmarkError } from "./errors.js";
import { OpenAICompatEngine } from "./openai_compat.js";
import type { EngineConfig } from "./config.js";
import type { Engine } from "./engines.js";

export function makeEngine(config: EngineConfig): Engine {
  return new OpenAICompatEngine(config);
}
