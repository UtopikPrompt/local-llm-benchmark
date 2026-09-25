/**
 * Bridge between the Astro UI and the Python CLI backend.
 *
 * The Python CLI is the single source of truth for benchmark runs (ADR-003).
 * This bridge talks to it over HTTP (`/api/runs`) using `fetch()`, which runs
 * server-side via the Node adapter.
 */

const API_URL = '/api/runs';

/**
 * Fetch all benchmark runs from the Python CLI and normalize them to the
 * shape the UI expects.
 *
 * @returns {Promise<Array<{
 *   id: string;
 *   model: string;
 *   prompt: string | null;
 *   completion: string | null;
 *   qualityScores: Record<string, number>;
 *   createdAt: string;
 * }>}
 */
export async function fetchRuns() {
    try {
        const res = await fetch(API_URL);
        if (!res.ok) {
            throw new Error(`Request failed with status ${res.status}`);
        }

        const runs = await res.json();
        return runs.map((run) => ({
            id: run.run_id,
            model: run.model,
            prompt: run.prompt,
            completion: run.completion,
            qualityScores: run.qualityScores,
            createdAt: run.created_at,
        }));
    } catch (error) {
        // Safe fallbacks for the UI to render gracefully.
        return [];
    }
}

/**
 * Fetch quality scores from the Python CLI and return a Map of run IDs to scores.
 *
 * @returns {Promise<Map<string, Map<string, number>>>}
 */
export async function getScores() {
    try {
        const res = await fetch(`${API_URL}/runs?action=scores`);
        if (!res.ok) {
            throw new Error(`Request failed with status ${res.status}`);
        }

        const scores = await res.json();
        const result = new Map();
        scores.forEach(runScores => {
            const runId = runScores.run_id;
            if (runId && result.has(runId)) {
                result.set(runId, {
                    accuracy: runScores.accuracy,
                    faithfulness: runScores.faithfulness,
                    groundedness: runScores.groundedness,
                    instructionFollowing: runScores.instructionFollowing,
                    reasoning: runScores.reasoning,
                    relevance: runScores.relevance,
                    helpfulness: runScores.helpfulness,
                    honesty: runScores.honesty,
                    harmlessness: runScores.harmlessness,
                });
            }
        });
        return result;
    } catch (error) {
        console.error("getScores error:", error);
        return new Map();
    }
}

// Bridge-prefixed exports for TypeScript declarations
export const bridgeFetchRuns = fetchRuns;
export const bridgeGetScores = getScores;

/**
 * Fetch a single benchmark run by id.
 *
 * @param {string} runId - The run identifier.
 * @returns {Promise<{run: {
 *   id: string;
 *   model: string;
 *   prompt: string | null;
 *   completion: string | null;
 *   qualityScores: Record<string, number>;
 *   createdAt: string;
 * } | null>}}
 */
export async function getRun(runId) {
    try {
        const res = await fetch(API_URL);
        if (!res.ok) {
            throw new Error(`Request failed with status ${res.status}`);
        }

        const runs = await res.json();
        const run = runs.find((r) => r.run_id === runId);
        return {
            run: run
                ? {
                    id: run.run_id,
                    model: run.model,
                    prompt: run.prompt,
                    completion: run.completion,
                    qualityScores: run.qualityScores,
                    createdAt: run.created_at,
                }
                : null,
        };
    } catch (error) {
        return { run: null };
    }
}
