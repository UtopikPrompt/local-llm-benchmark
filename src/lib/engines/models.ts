import type { Engine } from './engines.js';

/**
 * Fetch the engine's models list from its OpenAI-compatible API.
 *
 * @param engine - The engine to list models for.
 * @returns The list of models advertised by the engine.
 */
export async function listModels(engine: Engine): Promise<string[]> {
	return engine.list_models();
}
