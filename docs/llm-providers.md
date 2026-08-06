# LLM Providers

The AI Cortex talks to any **OpenAI-compatible** chat-completions endpoint.
Configuration is entirely env-driven (`backend` container reads `.env`), so
swapping providers is a copy-paste change with zero code edits.

Provider choice:

- `LLM_PROVIDER=auto` (default) → uses the real provider when `LLM_API_KEY` is
  set, otherwise falls back to the **deterministic mock provider**.
- `LLM_PROVIDER=mock` → force the mock provider even with a key set.

## Mock provider fallback (no key needed)

Leave `LLM_API_KEY=` empty and the whole product works in dev/test against a
deterministic, schema-valid mock: blueprint reviews, hurdle generation,
strategic options, ghost decisions, and post-mortems all produce valid output
seeded from the prompt text. This is what the test suite uses.

---

## DeepSeek

```bash
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-your-deepseek-key
LLM_MODEL=deepseek-chat
LLM_PROVIDER=auto
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=3
```

## OpenAI

```bash
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-openai-key
LLM_MODEL=gpt-4o-mini
LLM_PROVIDER=auto
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=3
```

## Ollama (local, free)

```bash
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama          # any non-empty placeholder
LLM_MODEL=llama3.1
LLM_PROVIDER=auto
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=3
```

## Optional: token-cost tracking

Per-1k-token pricing enables `cost_usd` on LLM responses (used by usage
metering). Set both to `0.0` to disable cost tracking:

```bash
LLM_COST_PER_1K_INPUT_TOKENS=0.0
LLM_COST_PER_1K_OUTPUT_TOKENS=0.0
```

> **Tip:** every LLM response is validated against a Pydantic schema by the
> structured-output bridge (`app/agents/bridge.py`); invalid output triggers a
> repair-retry loop (max 2) before failing gracefully. The engine clamps any
> mechanical deltas to physical possibility, so a weak local model can't
> corrupt a simulation.
