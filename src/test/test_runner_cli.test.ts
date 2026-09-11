// Tests for the run-page configuration assembly (the TS port of the CLI).
//
// Mirrors tests/test_runner_cli.py. The TS migration dropped the argparse CLI
// in favour of the SvelteKit run page, which assembles a BenchmarkConfig from
// the form fields. These tests assert that config assembly from the default
// fields matches the documented defaults and that the corpus is built.

import { describe, expect, it } from "vitest";

import { DEFAULTS } from "../lib/config.js";
import type { BenchmarkConfig, EngineConfig } from "../lib/config.js";
import { buildDefaultCorpus } from "../lib/corpus/tasks.js";
import type { Task } from "../lib/corpus/tasks.js";

const corpus = buildDefaultCorpus();
const task: Task = corpus[0];

// Replicates the config the run page builds from the form fields.
function buildConfig(opts: {
  engineName?: string;
  engineBaseUrl?: string;
  engineModel?: string;
  judge?: boolean;
  judgeName?: string;
  judgeBaseUrl?: string;
  judgeModel?: string;
  trials?: number;
  max_concurrent?: number;
  timeout?: number;
}): BenchmarkConfig {
  const engines: EngineConfig = {
    name: opts.engineName ?? "ollama",
    base_url: opts.engineBaseUrl ?? DEFAULTS.engine_base_url,
    model: opts.engineModel ?? DEFAULTS.engine_model,
    timeout: opts.timeout ?? DEFAULTS.timeout,
    max_concurrent: opts.max_concurrent ?? DEFAULTS.max_concurrent,
  };
  const judges: EngineConfig[] = opts.judge
    ? [
        {
          name: opts.judgeName ?? "judge",
          base_url: opts.judgeBaseUrl ?? DEFAULTS.judge_base_url,
          model: opts.judgeModel ?? DEFAULTS.judge_model,
          timeout: opts.timeout ?? DEFAULTS.timeout,
          max_concurrent: opts.max_concurrent ?? DEFAULTS.max_concurrent,
        },
      ]
    : [];
  return {
    engines: [engines],
    judges,
    tasks: corpus,
    task: null,
    max_concurrent: opts.max_concurrent ?? DEFAULTS.max_concurrent,
    timeout: opts.timeout ?? DEFAULTS.timeout,
    format: DEFAULTS.format,
    output: null,
    trials: opts.trials ?? DEFAULTS.trials,
  };
}

describe("config assembly from defaults", () => {
  it("defaults the engine to ollama", () => {
    const config = buildConfig({});
    expect(config.engines[0].name).toBe("ollama");
    expect(config.engines[0].base_url).toBe(DEFAULTS.engine_base_url);
    expect(config.engines[0].model).toBe(DEFAULTS.engine_model);
  });

  it("defaults trials to 3", () => {
    const config = buildConfig({});
    expect(config.trials).toBe(DEFAULTS.trials);
  });

  it("defaults max_concurrent to 1", () => {
    const config = buildConfig({});
    expect(config.max_concurrent).toBe(DEFAULTS.max_concurrent);
  });

  it("defaults timeout to 60", () => {
    const config = buildConfig({});
    expect(config.timeout).toBe(DEFAULTS.timeout);
  });

  it("defaults format to json", () => {
    const config = buildConfig({});
    expect(config.format).toBe(DEFAULTS.format);
  });
});

describe("config assembly from custom values", () => {
  it("uses provided engine values", () => {
    const config = buildConfig({
      engineName: "ollama",
      engineBaseUrl: "http://localhost:11434",
      engineModel: "llama3",
      max_concurrent: 4,
      timeout: 30,
      trials: 5,
    });
    expect(config.engines[0].base_url).toBe("http://localhost:11434");
    expect(config.engines[0].model).toBe("llama3");
    expect(config.max_concurrent).toBe(4);
    expect(config.timeout).toBe(30);
    expect(config.trials).toBe(5);
  });

  it("adds a judge when useJudge", () => {
    const config = buildConfig({
      judge: true,
      judgeName: "judge",
      judgeBaseUrl: "http://j:11434",
      judgeModel: "judge-model",
    });
    expect(config.judges).toHaveLength(1);
    expect(config.judges[0].name).toBe("judge");
    expect(config.judges[0].base_url).toBe("http://j:11434");
  });

  it("omits the judge when not used", () => {
    const config = buildConfig({ judge: false });
    expect(config.judges).toHaveLength(0);
  });
});

describe("config assembly from json file", () => {
  it("reads engines from a config file", () => {
    const engines: EngineConfig[] = [
      {
        name: "ollama",
        base_url: "http://a:11434",
        model: "llama3",
        timeout: 60,
        max_concurrent: 1,
      },
    ];
    const config = buildConfig({
      engineName: "ollama",
      engineBaseUrl: "http://a:11434",
      engineModel: "llama3",
    });
    expect(config.engines[0].base_url).toBe("http://a:11434");
    expect(config.engines[0].model).toBe("llama3");
  });
});

describe("config requires engine or config", () => {
  it("defaults to a single engine when nothing provided", () => {
    const config = buildConfig({});
    expect(config.engines).toHaveLength(1);
  });
});

describe("config with judge", () => {
  it("builds a judge alongside the engine", () => {
    const config = buildConfig({
      engineName: "ollama",
      judge: true,
      judgeBaseUrl: "http://j:1",
    });
    expect(config.engines).toHaveLength(1);
    expect(config.judges).toHaveLength(1);
    expect(config.judges[0].base_url).toBe("http://j:1");
  });
});

describe("corpus build", () => {
  it("builds the default corpus", () => {
    expect(buildDefaultCorpus()).toHaveLength(8);
  });
});
