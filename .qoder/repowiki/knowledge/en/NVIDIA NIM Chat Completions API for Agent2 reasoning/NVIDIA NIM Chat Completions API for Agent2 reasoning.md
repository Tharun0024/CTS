---
kind: external_dependency
name: NVIDIA NIM Chat Completions API for Agent2 reasoning
slug: nvidia-nim
category: external_dependency
category_hints:
    - vendor_identity
    - auth_protocol
scope:
    - '**'
source_files:
    - decision/llm_provider.py
    - .env.example
    - agent2/config.py
---

### Identity & Role
- The project uses NVIDIA's hosted inference service at `https://integrate.api.nvidia.com/v1` as the LLM provider for Agent2 reasoning/interpretation. It is NOT used to make coverage decisions — only to interpret policy criteria and format structured JSON.

### Integration Point
- `decision/llm_provider.py::NVIDIAProvider` implements a zero-dependency urllib-based client that posts an OpenAI-compatible `/chat/completions` payload with `response_format: json_object`, `temperature: 0.1`, `max_tokens: 512`, and `chat_template_kwargs: {enable_thinking: False}`.
- Environment variables: `NVIDIA_API_KEY`, `NVIDIA_MODEL` (default `z-ai/glm-5.2`), `NVIDIA_API_URL` (default `https://integrate.api.nvidia.com/v1`).
- `agent2/config.py` also exposes `NVIDIA_BASE_URL` which falls back to `NVIDIA_API_URL`; `agent2/workflow/orchestrator.py` imports from there for its own Gemini-era path but the integrated V1 pipeline uses `decision.llm_provider`.

### Auth Protocol
- Bearer token in `Authorization` header; model name passed in the `model` field of the chat-completions request body.

### Stable Usage Notes
- The endpoint URL is normalized by stripping trailing slashes and appending `/chat/completions` if missing.
- 429 → rate-limit error; 401 → unauthorized; network/timeout errors fail closed.
- A legacy `GeminiProvider` (`GOOGLE_API_KEY`) and `OpenRouterProvider` (`OPENROUTER_API_KEY`) exist in the same file but are not part of the active V1 Agent2 flow.