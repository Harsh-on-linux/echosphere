# AGENTS.md — VaayuMitra Build Rules

> This file is the source of truth for any AI coding agent (or human) working in this repo.
> Follow these rules strictly. The project is VaayuMitra + Agora Conversational AI Engine.

## 1. Core Constraints

- **Agora is central.** All voice flows through Agora Conversational AI Engine (`SD-RTN` + `RTC/RTM` + `ASR->LLM->TTS`). Never call LLM directly from frontend. Use `POST /join` via Agents SDK or REST. Frontend only does `token` + `channel` + RTC.
- **Keep idea intact.** Personas: farmer/fisherman/disaster. Data: real IMD APIs. Languages: regional voice. Telephony-first design stays.
- **Free-tier first.** Use `credential_mode: managed` for LLM/TTS (gpt-4o-mini, MiniMax) unless Indic needed. Indic via Sarvam BYOK only on `₹100` free. Stay inside `300 min` free. Never enable Cloud Recording/extra services unless asked.
- **Short, factual output.** No filler praise. When referencing code, use `file_path:line_number`.

## 2. Required Reading Before Any Edit

Before changing code, read:
1. `research.md` — all Agora/IMD/Sarvam pricing + API details
2. `plan.md` — phased implementation plan
3. This `AGENTS.md`

For live Agora docs, prefer `https://mcp.agora.io` or `docs.agora.io/llms.txt` over stale memory.

## 3. Commit Policy — After Each Step/Substep

**MANDATORY:** After completing **every** Step or Sub-step in `plan.md` (e.g., `0.1`, `0.2`, `1.1`), you **MUST** commit.

### 3.1 Commit Workflow
```bash
git status
git diff --stat
git log --oneline -5
git add <only intended files>   # never add secrets (.env) — they are gitignored
git commit -m "<type>(scope): <short summary>

<optional body: what changed, verification>"
# Do NOT push unless user explicitly says: "push" or "create PR"
```

### 3.2 Commit Types
- `feat` — new feature
- `fix` — bug fix
- `docs` — research.md / plan.md / AGENTS.md / README
- `chore` — tooling, config, setup
- `refactor` — no behavior change
- `test` — tests

### 3.3 Commit Message Format (Conventional Commits)
```
feat(phase0): add Agora project env and IMD whitelisting docs
fix(rtc): set idle_timeout 120 to prevent free-tier burn
docs(research): update Sarvam pricing Aug 2026
```

### 3.4 Granularity Examples (from plan.md)
| Completed | Commit Message | Files |
|-----------|---------------|-------|
| `Step 0.1` | `chore(phase0): create Agora/Sarvam/IMD accounts and .env.example` | `.env.example`, `research.md` |
| `Step 0.2` | `chore(tools): install Agora CLI, bun, agora-agents SDK` | `package.json`, `requirements.txt` |
| `Step 0.3` | `feat(init): scaffold vaayumitra via agora init python template` | `frontend/`, `backend/`, `.env` |
| `Step 1.1` | `chore(structure): define folder layout data/backend/frontend` | `data/imd_districts.json`, `backend/` |
| `Step 1.2` | `feat(backend): add FastAPI skeleton + imd_client + location_resolver` | `backend/main.py`, `imd_client.py`, `location_resolver.py` |
| `Step 1.3` | `feat(token): add POST /api/token RTC+RTM generation` | `backend/main.py`, `frontend/api/token.ts` |
| `Step 2.1` | `feat(voice): wire managed Deepgram/OpenAI/MiniMax voice loop` | `backend/main.py` |
| `Step 2.2` | `feat(ui): add VoiceOrb, LiveTranscript, IMDSourceCard` | `frontend/src/components/*` |
| `Step 2.3` | `fix(rtc): add leave handler and idle_timeout guard` | `backend/main.py`, `frontend/...` |
| `Step 3.1` | `feat(imd): add 10 IMD endpoint wrappers with 5m cache` | `backend/imd_client.py` |
| `Step 3.2` | `feat(mcp): expose FastMCP tools at /mcp` | `backend/mcp_server.py` |
| `Step 3.3` | `feat(agent): connect MCP to LLM via mcp_servers` | `backend/main.py` |
| ... | ... | ... |

**If a step has sub-tasks, commit after each sub-task, not just phase end.** Example: Phase 3 has 3.1, 3.2, 3.3, 3.4 = 4 commits.

### 3.5 Before Every Commit — Checks
1. `Test-Path -LiteralPath .env` — ensure `.env` is gitignored (`git check-ignore .env` should succeed).
2. Run relevant verification from `plan.md` (e.g., `bun run dev` + `curl /api/token` + `agora project doctor`).
3. Review diff — no secrets, no accidental `.pyc`, `node_modules`.
4. Stage **only** intended files.

### 3.6 Never Commit
- `.env`, `*.pem`, `customer_secret`, `app_certificate` plaintext outside `.env.example`
- Large binaries (`*.wav` voiceprints >1MB — host at URL, not in repo)
- `node_modules/`, `.venv/`, `dist/`, `build/`

## 4. Branch & PR Rules
- Work on `main` for hackathon solo. If team >2, create `feat/<phase-step>` branches: `feat/phase3-mcp`.
- PR title = commit style, e.g., `feat(phase3): add IMD MCP integration`.
- Do NOT force-push, skip hooks, or amend failed commits — create a new fix commit.
- Push/PR only when user explicitly requests.

## 5. Verification Before Marking Step Done
After each step, prove it before committing:
- `agora project doctor` green (if touched Agora)
- `POST /api/token` returns tokens
- `Start conversation` audio loop works (RTC)
- `GET /agents/{id}/history` or `/turns` returns data (if agent)
- `pytest` or `curl /mcp` for backend tools
- No lingering agents: `agora console > usage` shows 0 active

If blocked, keep todo `in_progress` and add follow-up todo describing blocker — do not mark completed.

## 6. Coding Standards
- **SDK preference:** `agora-agents` Python (`agora_agent`) or TS (`agora-agents`) over raw REST, unless raw payload needed.
- **Tokens:** Generate server-side. Never expose `app_certificate` to browser.
- **Caching:** IMD responses TTL 300s.
- **Languages:** Use `turn_detection.language` + `asr.params.language` together; Sarvam `unknown` for auto.
- **File edits:** Read before edit, preserve indentation, check region after edit.

## 7. Example End-to-End Commit Sequence (One Step)
```bash
# After finishing Step 1.2 — backend skeleton
git status
git diff backend/main.py
git add backend/main.py backend/imd_client.py backend/location_resolver.py backend/mcp_server.py data/imd_districts.json
git commit -m "feat(backend): scaffold FastAPI + imd_client + location_resolver with mock cache

- adds TTL 300s cache, rapidfuzz resolver, sample IMD JSON fallback
- verification: pytest backend/tests/test_resolver.py passes"
```

## 8. Help & Docs
- Agora Skills: `npx skills add AgoraIO/skills`
- Agora MCP: `https://mcp.agora.io`
- Quickstart: `docs.agora.io/en/ai/get-started/quickstart`
- Start/Stop: `docs.agora.io/en/ai/build/start-stop-agent`
- Pricing: `docs.agora.io/en/ai/reference/pricing`

> Violating commit granularity (batching multiple phases into one commit) = harder rollback + judge can't see progress. Commit small, commit often.
