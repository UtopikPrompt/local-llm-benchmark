// Type declarations for the untyped bridge.js module.
// Provides concrete types so relative imports resolve and are type-checked.

export interface QualityScores {
    accuracy: number;
    faithfulness: number;
    groundedness: number;
    instructionFollowing: number;
    relevance: number;
    helpfulness: number;
    honesty: number;
    harmlessness: number;
}

export interface Runs {
    id: string;
    model: string;
    prompt: string;
    completion: string;
    qualityScores: QualityScores;
    createdAt: string;
}

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

