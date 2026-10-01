/**
 * Server-side handler for the `/api/runs` route.
 *
 * The GET handler shells out to the Python CLI (single source of truth, ADR-003)
 * and maps BenchmarkRun rows to the unified frontend shape.
 */

import { execFileSync } from 'node:child_process';

const CLI_RESULT = process.env.LOCAL_LLM_BENCHMARK_CLI_RESULT ?? '/workspaces/local-llm-benchmark';
const CLI_ARGS = ['-m', 'local_llm_benchmark', 'list-results', '--json'];

export async function handleRuns() {
    try {
        const output = execFileSync('python', CLI_ARGS, {
            cwd: CLI_RESULT,
            encoding: 'utf-8',
            stdio: ['ignore', 'pipe', 'pipe'],
        });

        const data = JSON.parse(output);

        // CLI returns [] when there are no runs.
        if (!Array.isArray(data)) {
            return new Response(JSON.stringify({ error: 'Unexpected CLI response' }), {
                status: 502,
                headers: { 'content-type': 'application/json' },
            });
        }

        const runs = data.map((run) => ({
            id: run.run_id,
            model: run.model,
            prompt: run.prompt ?? null,
            completion: run.completion ?? null,
            qualityScores: run.scores ?? {},
            createdAt: run.created_at,
        }));

        return new Response(JSON.stringify(runs), {
            status: 200,
            headers: { 'content-type': 'application/json' },
        });
    } catch (error) {
        return new Response(JSON.stringify({ error: 'Failed to fetch runs', detail: String(error) }), {
            status: 502,
            headers: { 'content-type': 'application/json' },
        });
    }
}

/**
 * Handle the GET request for scores action.
 *
 * @returns {Response} JSON Response with quality scores.
 */
export function handleScores() {
    try {
        const output = execFileSync('python', ['-m', 'local_llm_benchmark', 'list-scores', '--json'], {
            cwd: CLI_RESULT,
            encoding: 'utf-8',
            stdio: ['ignore', 'pipe', 'pipe'],
        });

        const data = JSON.parse(output);

        // CLI returns an object mapping run_id -> scores when --scores flag is used
        // e.g., {"run_id_1": {accuracy: 0.9, ...}, "run_id_2": {accuracy: 0.8, ...}}
        return new Response(JSON.stringify(data), {
            status: 200,
            headers: { 'content-type': 'application/json' },
        });
    } catch (error) {
        return new Response(JSON.stringify({ error: 'Failed to fetch scores', detail: String(error) }), {
            status: 502,
            headers: { 'content-type': 'application/json' },
        });
    }
}
