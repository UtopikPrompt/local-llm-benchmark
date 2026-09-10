// Central error handler. Returns a typed error so callers can branch without
// catching exceptions inline.
export interface BenchmarkError {
	code: string;
	message: string;
	details?: unknown;
}

export class BenchmarkError extends Error implements BenchmarkError {
	code: string;
	details?: unknown;

	constructor(code: string, message: string, details?: unknown) {
		super(message);
		this.name = 'BenchmarkError';
		this.code = code;
		this.details = details;
	}
}

export class ConfigError extends BenchmarkError {
	constructor(message: string, details?: unknown) {
		super('CONFIG', message, details);
	}
}

export class NetworkError extends BenchmarkError {
	constructor(message: string, details?: unknown) {
		super('NETWORK', message, details);
	}
}

export class ValidationError extends BenchmarkError {
	constructor(message: string, details?: unknown) {
		super('VALIDATION', message, details);
	}
}

export class NotFoundError extends BenchmarkError {
	constructor(message: string, details?: unknown) {
		super('NOT_FOUND', message, details);
	}
}
