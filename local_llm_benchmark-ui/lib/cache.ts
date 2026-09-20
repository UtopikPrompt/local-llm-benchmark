// local_llm_benchmark-ui/lib/cache.ts — thin client wrapper around the Python cache bridge.
//
// The Python process (see ../api/cache.py) exposes a small JSON API. This
// module only translates that JSON into the shapes the Astro UI expects.
//
// NOTE: This project is CommonJS-only (package.json has no "type": "module"),
// so these files must use CommonJS syntax.

type Run = {
  run_id: string;
  engine: string;
  model: string;
  benchmark: string;
  seed: number;
  temperature: number;
  max_tokens: number;
  created_at: string;
  endpoint: string;
  num_examples: number;
  num_tokens: number;
  ttft: number;
  tokens_per_sec: number;
};

type Scores = {
  [dimension: string]: number;
};

const API_BASE = "/api/cache";

function request(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["content-type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  return fetch(API_BASE + path, opts).then((res) => {
    return res.json().then((data) => ({ status: res.status, data }));
  });
}

/** List all cached runs (metadata only). */
export function listRuns() {
  return request("GET", "/runs").then((r) => r.data.runs);
}

/** Get a single run record (metadata + cached scores). */
export function getRun(runId) {
  return request("GET", `/run/${encodeURIComponent(runId)}`).then((r) => r.data);
}

/** Get the raw per-dimension scores for a run. */
export function getScores(runId) {
  return request("GET", `/scores/${encodeURIComponent(runId)}`).then((r) => r.data);
}

/** Invalidate (delete) a cached run record. */
export function invalidateRun(runId) {
  return request("POST", `/invalidate/${encodeURIComponent(runId)}`).then((r) => r.data);
}
