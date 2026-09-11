// OpenAI-compatible engine client. Talks to any server exposing an OpenAI
// chat-completions API (Ollama, LM Studio, ...). All network I/O is async.

import { BenchmarkError, NetworkError } from "../errors.js";
import type { Engine } from "./engines.js";
import type { EngineConfig } from "../config.js";

function joinUrl(base: string, path: string): string {
  return `${base.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

interface ChatMessage {
  role: string;
  content?: string;
  reasoning?: string;
}

interface ChatChoices {
  message?: ChatMessage;
}

interface ChatResponse {
  choices?: Array<ChatChoices>;
}

interface ModelsResponse {
  data?: Array<{ id?: string }>;
}

export class OpenAICompatEngine implements Engine {
  config: EngineConfig;
  private modelId: string | null = null;

  get name(): string {
    return this.config.name;
  }

  get model(): string {
    return this.modelId || this.config.model;
  }

  get base_url(): string {
    return this.config.base_url;
  }

  get timeout(): number {
    return this.config.timeout;
  }

  get max_concurrent(): number {
    return this.config.max_concurrent;
  }

  constructor(config: EngineConfig) {
    this.config = config;
  }

  async *chat(
    messages: Array<{ role: string; content: string }>,
    options: { max_tokens: number; stream: boolean },
  ): AsyncGenerator<string> {
    const model = this.modelId || this.config.model;
    const payload = {
      model,
      messages,
      max_tokens: options.max_tokens,
      stream: options.stream,
    };

    let response: Response;
    try {
      response = await fetch(
        joinUrl(this.config.base_url, "v1/chat/completions"),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify(payload),
        },
      );
    } catch (error) {
      throw new NetworkError("Failed to chat with engine", error);
    }

    if (!response.ok) {
      throw new BenchmarkError(
        "INVALID",
        `${response.status} ${response.statusText}`,
        {
          status: response.status,
          statusText: response.statusText,
        },
      );
    }

    if (options.stream) {
      const reader = response.body?.getReader();
      if (!reader) {
        throw new BenchmarkError("INVALID", "empty stream");
      }
      const decoder = new TextDecoder();
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const text = decoder.decode(value, { stream: true });
          for (const line of text.split("\n")) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith("data:")) continue;
            if (trimmed === "data: [DONE]") break;
            const data = trimmed.slice("data:".length).trim();
            try {
              const parsed = JSON.parse(data) as ChatResponse;
              const message = parsed.choices?.[0]?.message;
              const token = message?.content ?? message?.reasoning;
              if (token) yield token;
            } catch {
              // ignore malformed SSE lines
            }
          }
        }
      } catch {
        throw new BenchmarkError("INVALID", "stream error");
      }
      return;
    }

    const data = (await response.json()) as ChatResponse;
    const choices = data.choices;
    if (!choices?.[0]?.message) {
      throw new BenchmarkError("INVALID", "empty completion");
    }
    const message = choices[0].message;
    if (!message) {
      throw new BenchmarkError("INVALID", "empty completion");
    }
    yield message.content ?? message.reasoning ?? "";
    return;
  }

  list_models(): Promise<string[]> {
    return fetch(joinUrl(this.config.base_url, "v1/models"))
      .then((response) => {
        if (response.status !== 200) {
          return [];
        }
        return response
          .json()
          .then(
            (data: ModelsResponse) =>
              data.data
                ?.map((model: { id?: string }) => model.id ?? "")
                .filter(Boolean) ?? [],
          );
      })
      .catch(() => []);
  }

  async close(): Promise<void> {
    // The engine uses the global `fetch`, which is a persistent, shared
    // runtime capability rather than a per-engine connection, so there is no
    // dedicated client to release. This resolves to signal that the engine
    // has been closed so the runner can release the shared Semaphore in
    // `finally`.
    return;
  }
}
