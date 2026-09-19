# Module — engine interface

## Contract

Every inference engine is accessed through an **OpenAI-compatible** interface:

- `POST /v1/chat/completions`
- **Seeded sampling** so the same model + seed yields comparable outputs across engines.

## Supported engines

- **vLLM**
- **llama.cpp** — `openai_server` mode
- **Ollama**
- **HuggingFace Transformers** — via `OpenAIWrapper`

## Design

- Each engine is a **plugin** implementing the shared interface. The same model run through two
  engines is compared apples-to-apples.
- Each engine is an **optional, separately installed dependency** — never a hard dependency of the
  CLI.
- New engines are additive: implement the same interface, register it, do not refactor existing ones.

## Guardrails

- Do not weaken seeded sampling for determinism.
- Do not add engines as hard dependencies.
- Keep the interface stable; engine-specific quirks live in the engine plugin, not shared code.
