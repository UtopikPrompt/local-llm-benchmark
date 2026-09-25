import * as bridge from '../bridge.js';

/**
 * List all cached benchmark runs
 * @returns {Promise<Array>} Array of benchmark runs
 */
export async function listRuns() {
    return bridge.fetchRuns();
}

/**
 * Get quality scores for cached benchmark runs
 * @returns {Promise<Array>} Array of runs with quality scores
 */
export async function getScores() {
    return bridge.getScores();
}

/**
 * Get a single benchmark run by id
 * @param {string} runId - The run identifier
 * @returns {Promise<{run: {id: string, model: string, prompt: string | null, completion: string | null, qualityScores: Record<string, number>, createdAt: string} | null}>}
 */
export async function getRun(runId) {
    return bridge.getRun(runId);
}
