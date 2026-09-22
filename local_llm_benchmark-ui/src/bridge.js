import { fetchRuns, getScores } from 'local_llm_benchmark';

/**
 * Bridge module for Python-JavaScript communication
 * Provides fetch functions for backend data access
 */

export async function fetchRuns() {
    try {
        const runs = await fetchRuns();
        // Transform runs to match expected interface
        return runs.map(run => ({
            id: run.run_id,
            model: run.model,
            prompt: run.prompt,
            completion: run.completion,
            qualityScores: run.scores,
            createdAt: run.created_at
        }));
    } catch (error) {
        console.error('fetchRuns error:', error);
        return [];
    }
}

export async function getScores() {
    try {
        const scores = await getScores();
        return scores.map(score => ({
            id: score.id,
            scores: score.scores
        }));
    } catch (error) {
        console.error('getScores error:', error);
        return [];
    }
}
