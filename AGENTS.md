# AGENTS.md

## Purpose
This repository implements a real-time visualization system for programming lab instruction.
The system continuously captures instructor speech, segments utterances, transcribes them, decides whether the content is programming-related and visualization-worthy, generates a structured `diagram_plan`, and then renders SVG for display in a web app.

The architecture is:

- Frontend: Next.js / TypeScript
- Backend: FastAPI / Python
- Python environment: uv
- Realtime transport: WebSocket
- AI providers: OpenAI and Claude
- Visualization pipeline: speech -> transcript -> analysis -> diagram_plan -> SVG

You must preserve this architecture unless explicitly instructed otherwise.

---

## Core development principles

1. Do not collapse the architecture.
   - Keep UI concerns in the frontend.
   - Keep AI orchestration, realtime processing, and business logic in the backend.
   - Do not move backend logic into Next.js API routes unless explicitly requested.

2. Preserve the intermediate representation.
   - Do not generate SVG directly from raw transcript when the task belongs in the main pipeline.
   - Prefer:
     - transcript
     - normalized_text
     - domain/visualization analysis
     - `diagram_plan`
     - SVG
   - Treat `diagram_plan` as the canonical semantic representation.

3. Favor explicit, inspectable logic.
   - Prefer typed schemas, clear service boundaries, and logged intermediate artifacts.
   - Avoid hidden coupling between unrelated modules.
   - Make debugging easy.

4. Optimize for research iteration, not cleverness.
   - This project is experimental and will evolve.
   - Write code so prompts, providers, thresholds, and schemas can be changed safely.
   - Prefer extensibility over premature abstraction.

5. Keep realtime behavior robust.
   - Assume audio arrives continuously.
   - Assume utterances are segmented by silence/VAD and possibly corrected later.
   - Avoid blocking operations in the realtime path where possible.

---

## Repository expectations

When working in this repository, assume the following high-level structure:

- `frontend/`: Next.js UI
- `backend/`: FastAPI backend
- `backend/app/api/websocket/`: WebSocket endpoints
- `backend/app/services/audio/`: VAD, chunk buffering, utterance segmentation
- `backend/app/services/stt/`: speech-to-text
- `backend/app/services/llm/`: provider abstraction and model integrations
- `backend/app/services/analysis/`: domain filtering, visualization decisions, diagram planning
- `backend/app/services/generation/`: SVG generation and sanitization
- `backend/app/services/orchestration/`: realtime pipeline control
- `backend/app/schemas/`: Pydantic schemas
- `backend/app/prompts/`: prompt assets
- `backend/scripts/`: evaluation, replay, and experimental scripts

If the actual repo differs, adapt carefully but preserve the intent of these boundaries.

---

## Technology-specific rules

### Frontend rules
- Use Next.js with TypeScript.
- Keep frontend responsibilities limited to:
  - microphone/audio capture
  - UI state
  - WebSocket communication
  - transcript display
  - SVG rendering
  - debug/status display
- Do not place LLM orchestration logic in the frontend.
- Do not place domain classification logic in the frontend except for trivial UI-only checks.

### Backend rules
- Use FastAPI for backend APIs and WebSocket endpoints.
- Use Python for orchestration, provider calls, analysis, and SVG generation.
- Use Pydantic models for structured request/response/event payloads.
- Prefer async endpoints and async services where realtime behavior benefits.

### Python environment rules
- Use `uv` for dependency management and execution.
- Prefer commands such as:
  - `uv sync`
  - `uv run ...`
- Do not introduce ad hoc `pip install` instructions when `uv` should be used instead.

---

## AI pipeline rules

### Required pipeline shape
For core visualization tasks, the expected pipeline is:

1. Audio chunk ingestion
2. Buffering / utterance segmentation
3. STT
4. Transcript normalization
5. Programming-domain relevance decision
6. Visualization-necessity decision
7. `diagram_plan` generation
8. SVG generation
9. SVG sanitization / validation
10. UI delivery and logging

Do not skip steps 5-7 unless the user explicitly requests a simplified prototype.

### Domain filtering
- The system should reject clearly irrelevant content.
- Example of irrelevant content:
  - cooking instructions
  - unrelated casual chat
  - administrative talk with no visualization value
- The programming-related decision should be explicit and inspectable.

### Visualization gating
- Even if content is programming-related, do not always generate a diagram.
- Prefer no diagram when:
  - the utterance is procedural/admin-only
  - the content has no useful spatial/structural/process representation
  - the content duplicates a very recent diagram with negligible change

### `diagram_plan` rules
- `diagram_plan` is the semantic source of truth before SVG generation.
- It should be JSON-serializable and schema-validated.
- Prefer stable IDs for nodes and edges when feasible.
- Keep it descriptive enough to support replay, evaluation, and provider comparison.

### SVG rules
- Generate browser-renderable SVG.
- No script tags.
- Sanitize output before returning to the frontend.
- Preserve readability and layout clarity over decorative complexity.

---

## WebSocket rules

Assume the primary realtime endpoint is conceptually similar to:

- `WS /ws/audio`

Expected client->server event families:
- `session.start`
- `audio.chunk`
- `utterance.flush`
- `session.stop`

Expected server->client event families:
- `ack`
- `transcript.partial`
- `transcript.final`
- `analysis.result`
- `diagram.plan`
- `svg.result`
- `pipeline.status`
- `error`

When implementing or modifying WebSocket behavior:
- keep event names stable unless explicitly refactoring both ends
- preserve structured payloads
- avoid silent breaking changes
- update schemas and frontend handling together

---

## Schema and typing rules

- Use typed models for:
  - transcript payloads
  - analysis results
  - websocket events
  - `diagram_plan`
  - SVG response payloads
- Prefer explicit enums/literals where appropriate.
- Avoid passing around loosely structured dictionaries when a schema should exist.
- If adding new fields, preserve backward compatibility where practical.

---

## Provider abstraction rules

- Keep OpenAI and Claude access behind a provider abstraction layer.
- Do not hard-wire provider-specific logic into unrelated services.
- New providers should be pluggable with minimal pipeline disruption.
- Prompt construction should be isolated from transport/client code.
- Log provider/model identifiers where useful for experiments and debugging.

---

## Logging and evaluation rules

This project is research-oriented. Logging matters.

Preserve or improve logging for:
- session identifiers
- utterance identifiers
- chunk identifiers
- raw transcript
- normalized transcript
- domain decision
- visualization decision
- `diagram_plan`
- SVG generation result
- latency per stage
- provider/model used
- prompt version when applicable

When possible, changes should make offline replay/evaluation easier, not harder.

---

## Prompt management rules

- Keep prompts in dedicated prompt files or clearly isolated prompt builders.
- Do not scatter large prompt strings across unrelated files.
- If modifying prompts:
  - keep them readable
  - preserve versionability
  - avoid mixing prompt text with low-level transport code
- Prompt edits should not silently break schemas.

---

## Code quality rules

### General
- Make minimal, precise changes.
- Do not rewrite large areas without clear need.
- Preserve existing naming and structure when reasonable.
- Prefer simple, explicit implementations.

### Python
- Prefer type hints.
- Prefer small service functions/classes with clear responsibilities.
- Avoid monolithic files for orchestration-heavy logic.
- Keep FastAPI handlers thin; move logic into services.

### TypeScript
- Use clear types/interfaces for WebSocket events and UI state.
- Keep components focused.
- Avoid embedding protocol details everywhere; centralize them.

---

## Testing and validation rules

When making changes, validate at the appropriate level.

### Backend
At minimum, consider:
- schema validation
- service-level unit tests
- integration tests for pipeline stages when feasible

### Frontend
At minimum, consider:
- event handling correctness
- rendering behavior for transcript/status/SVG states

### Realtime path
If touching the audio or websocket pipeline, verify:
- event contract consistency
- partial/final transcript handling
- analysis event handling
- SVG update flow
- graceful behavior on provider failure

If you cannot run tests, state that clearly and explain what remains unverified.

---

## Performance rules

- Be careful with blocking operations inside websocket handlers.
- Prefer staged processing and clear status emission.
- Avoid unnecessary provider calls.
- Avoid regenerating diagrams when the result is clearly unnecessary.
- Respect the realtime nature of the system.

---

## Safety and failure-handling rules

- Treat provider/API failures as expected cases.
- Prefer explicit fallback behavior:
  - transcript-only return if diagram generation fails
  - preserve `diagram_plan` if SVG generation fails
  - keep last valid SVG if appropriate
- Do not fail silently.
- Emit structured errors where possible.

---

## When asked to implement features

When implementing a feature, prefer this order:
1. identify affected boundary (frontend, websocket, backend service, schema, prompt, storage)
2. update schema/contracts first if needed
3. implement backend logic
4. update frontend consumer
5. add or adjust tests
6. summarize what changed and any remaining risks

---

## When asked architectural questions

When asked for design advice in this repo:
- recommend solutions consistent with:
  - Next.js frontend
  - FastAPI backend
  - uv-managed Python environment
  - WebSocket realtime flow
  - `diagram_plan` as intermediate representation
- do not suggest architecture that discards these decisions unless explicitly asked for alternatives

---

## Forbidden shortcuts

Unless explicitly requested, do not:
- move the main backend into Next.js API routes
- bypass `diagram_plan` for the core pipeline
- hardcode provider behavior into random modules
- mix UI rendering logic into backend orchestration
- return unvalidated SVG directly from arbitrary model output
- replace `uv`-based workflow with ad hoc environment management

---

## Expected developer workflow

For Python/backend work, prefer commands in this style:
- `uv sync`
- `uv run uvicorn app.main:app --reload`
- `uv run pytest`

For frontend work, use the repo's existing package manager/scripts rather than inventing new ones.

Before finalizing substantial changes:
- check formatting/linting if configured
- check typing if configured
- check tests if available

If something cannot be verified locally, say so explicitly.

---

## Output expectations for Codex

When completing tasks in this repository, provide:
- a concise summary of what changed
- any schema or protocol changes
- any files that require coordinated frontend/backend updates
- any follow-up validation still needed

Be concrete. Do not be vague.