-- results table for engine runs (design §7)
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at TEXT NOT NULL DEFAULT (datetime('now')),
    model TEXT NOT NULL,
    status TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    latency_s REAL NOT NULL,
    throughput_toks_s REAL GENERATED ALWAYS AS (
        CASE
            WHEN latency_s > 0 THEN CAST(output_tokens AS REAL) / latency_s
            ELSE 0
        END
    ) STORED,
    prompt TEXT,
    response TEXT
);

CREATE INDEX IF NOT EXISTS idx_results_model ON results (model);
CREATE INDEX IF NOT EXISTS idx_results_status ON results (status);
CREATE INDEX IF NOT EXISTS idx_results_run_at ON results (run_at);