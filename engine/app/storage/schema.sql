-- Slice 3 storage schema for the inference run `results` table.
-- `throughput_toks_s` is a generated column: it is never written by the
-- caller and is always derived as output_tokens / latency.

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    model TEXT NOT NULL,
    tokenizer TEXT NOT NULL,
    created_at TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    latency REAL NOT NULL,
    ttfb REAL NOT NULL,
    throughput_toks_s REAL GENERATED ALWAYS AS (output_tokens / latency),
    system_prompt TEXT NOT NULL,
    seed INTEGER,
    temperature REAL,
    max_tokens INTEGER
);

CREATE INDEX IF NOT EXISTS idx_results_run_id ON results (run_id);
CREATE INDEX IF NOT EXISTS idx_results_model ON results (model);