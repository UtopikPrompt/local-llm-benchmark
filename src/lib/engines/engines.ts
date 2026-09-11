// This subfolder file exists so the engines' implementation modules can import
// a stable `Engine` type. The canonical definition (with `name`/`model`/
// `base_url`/`timeout`/`max_concurrent`) lives in the top-level `engines.ts`;
// we re-export it so there is a single definition.

export type { Engine } from "../engines.js";
export type { EngineConfig } from "../config.js";
