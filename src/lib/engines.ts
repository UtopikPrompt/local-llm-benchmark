// Engine abstraction: talks to a remote OpenAI-compatible chat-completions API.
export interface Engine {
  name: string;
  model: string;
  base_url: string;
  timeout: number;
  max_concurrent: number;

  chat(
    messages: Array<{ role: string; content: string }>,
    options: { max_tokens: number; stream: boolean },
  ): AsyncGenerator<string>;

  list_models(): Promise<string[]>;
}
