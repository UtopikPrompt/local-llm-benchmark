// Engine abstraction: talks to a remote OpenAI-compatible
// chat-completions API (Ollama, LM Studio, ...).

export interface EngineConfig {
  name: string;
  model: string;
  base_url: string;
  timeout: number;
  max_concurrent: number;
}

export interface Engine {
  config: EngineConfig;

  // `chat` streams the model's tokens, yielding one token at a time. Callers
  // may iterate eagerly (for the full text) or stream incrementally (to
  // measure time-to-first-token).
  chat(
    messages: Array<{ role: string; content: string }>,
    options: { max_tokens: number; stream: boolean },
  ): AsyncGenerator<string>;

  list_models(): Promise<string[]>;
}
