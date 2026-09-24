import { fetchRuns, getScores, getRun } from '../bridge.js';

/**
 * List all cached benchmark runs
 * @returns {Promise<Array>} Array of benchmark runs
 */
export async function listRuns() {
    return fetchRuns();
}

/**
 * Get quality scores for cached benchmark runs
 * @returns {Promise<Array>} Array of runs with quality scores
 */
export async function getScores() {
    return getScores();
}

/**
 * Get a single benchmark run by id
 * @param {string} runId - The run identifier
 * @returns {Promise<{run: {id: string, model: string, prompt: string | null, completion: string | null, qualityScores: Record<string, number>, createdAt: string} | null}>}
 */
export async function getRun(runId) {
    return getRun(runId);
}
