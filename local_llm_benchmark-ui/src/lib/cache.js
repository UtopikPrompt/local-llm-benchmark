import { fetchRuns, getScores } from '../bridge.js';

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
