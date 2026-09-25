// Type declarations for the untyped bridge.js module.
// Provides concrete types so relative imports resolve and are type-checked.

export interface RunMeta {
    id: string;
    model: string;
    prompt: string | null;
    completion: string | null;
    qualityScores: QualityScores;
    createdAt: string;
}

export interface GetRunResult {
    run: RunMeta | null;
}

// Exported for use in index.astro and other files
export interface QualityScores extends Map<string, number> {
    id: string;
    qualityScores: Map<string, number>;
    accuracy: number;
    faithfulness: number;
    groundedness: number;
    instructionFollowing: number;
    reasoning: number;
    relevance: number;
    helpfulness: number;
    honesty: number;
    harmlessness: number;
}

// The bridge.js module is untyped, so these declarations give relative
// imports (`from '../bridge'`) concrete types for type-checking.
declare const bridgeFetchRuns: () => Promise<Runs[]>;
declare const bridgeGetScores: () => Promise<QualityScores[]>;

declare const getRun: (runId: string) => Promise<{ run: RunMeta | null }>;

