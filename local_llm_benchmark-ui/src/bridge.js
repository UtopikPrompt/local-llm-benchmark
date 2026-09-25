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

// Bridge-prefixed exports for TypeScript declarations
export const bridgeFetchRuns = fetchRuns;
export const bridgeGetScores = getScores;
 * createdAt: string;
 * } | null >}
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
