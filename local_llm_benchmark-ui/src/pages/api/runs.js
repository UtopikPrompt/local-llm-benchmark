import { handleRuns, handleScores } from '../../lib/api/runs.js';

export async function GET({ request }) {
    const url = new URL(request.url);
    const action = url.searchParams.get('action');

    if (action === 'scores') {
        return handleScores();
    }
    return handleRuns();
}
