# PD Documentation Test Results

Tested: 2026-05-28
Agent: Codex with read-only explorer sub-agents
Repo: `agent-quickstart-python`

## Summary

- Total questions: 6
- Passed: 6
- L1 gaps: 0
- L2 gaps: 0
- Cross-ref issues: 0

The tree passed structural checks and a clean read-only content test. Source-verified drift found during review was fixed before the final content test.

## Results

### Setup & Build

| # | Question | Answer Correct? | Files Read | Level Loaded | Result |
| - | -------- | --------------- | ---------- | ------------ | ------ |
| 1 | How do I install dependencies and run the web + server dev stack? | Yes | `README.md`, `L0`, `L1/01_setup.md`, `L1/05_workflows.md`, `package.json` | L0+L1 sufficient | Pass |
| 2 | Which env vars are required and which process owns each? | Yes | `README.md`, `server/.env.example`, `L1/01_setup.md`, `L1/06_interfaces.md`, `L1/08_security.md`, `server/src/server.py`, `server/src/agent.py`, `web/next.config.ts` | L0+L1 sufficient | Pass |

### Test & Run

| # | Question | Answer Correct? | Files Read | Level Loaded | Result |
| - | -------- | --------------- | ---------- | ------------ | ------ |
| 3 | What does the verification suite cover, and what does `py_compile` not cover? | Yes | `L1/01_setup.md`, `L1/04_conventions.md`, `L2/verification_scripts.md`, `package.json`, `web/scripts/verify-api-contracts.ts`, `web/scripts/verify-local-proxy.ts`, `web/scripts/verify-local-fastapi.ts`, `server/scripts/run_fake_server.py` | L2 required | Pass |

### Conventions

| # | Question | Answer Correct? | Files Read | Level Loaded | Result |
| - | -------- | --------------- | ---------- | ------------ | ------ |
| 4 | How do I add a new backend endpoint exposed to the browser? | Yes | `L1/05_workflows.md`, `L1/06_interfaces.md`, `L2/verification_scripts.md`, `server/src/server.py`, `server/src/agent.py`, `web/next.config.ts`, `web/src/services/api.ts`, `web/scripts/verify-api-contracts.ts`, `web/scripts/verify-local-proxy.ts`, `web/scripts/verify-local-fastapi.ts` | L2 required | Pass |

### Development

| # | Question | Answer Correct? | Files Read | Level Loaded | Result |
| - | -------- | --------------- | ---------- | ------------ | ------ |
| 5 | Where do I change the agent prompt, voice, VAD, and model defaults? | Yes | `L1/02_architecture.md`, `L1/05_workflows.md`, `L1/06_interfaces.md`, `L2/managed_agent_config.md`, `server/src/agent.py` | L2 required | Pass |

### Deep Dive

| # | Question | Answer Correct? | Files Read | Level Loaded | Result |
| - | -------- | --------------- | ---------- | ------------ | ------ |
| 6 | How does token renewal keep RTC and RTM UIDs consistent? | Yes | `L1/02_architecture.md`, `L1/05_workflows.md`, `L1/06_interfaces.md`, `L1/07_gotchas.md`, `L1/08_security.md`, `L2/session_lifecycle.md`, `web/src/components/LandingPage.tsx`, `web/src/components/ConversationComponent.tsx`, `server/src/server.py` | L2 required | Pass |

## Recommended Fixes

- [x] Update `L0_repo_card.md` `Last Reviewed` to 2026-05-28.
- [x] Fix setup sequence and `agora-agents>=2.0.0` dependency wording in `L1/01_setup.md`.
- [x] Align `L1/02_architecture.md` rewrite snippet with `web/next.config.ts`.
- [x] Clarify hook-owned cleanup, FastAPI error detail shape, git conventions, and `py_compile` limits in `L1/04_conventions.md`.
- [x] Replace CI wording with local pre-ship checks in `L1/06_interfaces.md`.
- [x] Correct `AGENT_BACKEND_URL` trailing-slash behavior in `L1/07_gotchas.md`.
- [x] Fix `DEFAULT_GREETING` reference in `L2/managed_agent_config.md`.
- [x] Fix `GET /api/get_config` and current `getConfig({ channel, uid })` examples in `L2/session_lifecycle.md`.
- [x] Fix `py_compile` claims in `L2/verification_scripts.md`.
- [x] Replace stale Vite/Zustand/React Query `web/docs/ARCHITECTURE.md` content with the current Next.js + FastAPI shape.
- [x] Add `docs/ai/RECIPE.md` and mark this repo as an experimental base recipe in `L0_repo_card.md`.
- [x] Add `L1/L2/from_scratch_bootstrap.md` using the same recipe pattern as the Next.js quickstart: compact recipe contract plus detailed baseline implementation map in L2.

## Review Fix Retest

Retested: 2026-05-28

| Finding | Source checked | Docs changed | Result | Notes |
| ------- | -------------- | ------------ | ------ | ----- |
| Stale L0 review date | `git log`, `AGENTS.md` | `docs/ai/L0_repo_card.md` | Pass | Date now reflects this review. |
| `bun run setup` sequence drift | `package.json` | `docs/ai/L1/01_setup.md` | Pass | Setup sequence no longer lists `setup:deps`. |
| `py_compile` overclaimed import coverage | `package.json`, Python `py_compile` behavior | `docs/ai/L1/04_conventions.md`, `docs/ai/L1/L2/verification_scripts.md` | Pass | Docs now say syntax only and point to runtime checks. |
| FastAPI error detail shape | `server/src/server.py` | `docs/ai/L1/04_conventions.md` | Pass | Docs now describe string `detail`. |
| Session lifecycle method/signature drift | `web/src/services/api.ts`, `LandingPage.tsx` | `docs/ai/L1/L2/session_lifecycle.md` | Pass | L2 now uses `GET` and object-form `getConfig`. |
| Agent greeting constant drift | `server/src/agent.py` | `docs/ai/L1/L2/managed_agent_config.md` | Pass | Docs now reference the inline fallback string. |
| Stale web architecture template | `web/package.json`, `web/app/page.tsx`, `web/src/components/LandingPage.tsx`, `web/next.config.ts` | `web/docs/ARCHITECTURE.md` | Pass | Web doc now reflects Next.js App Router and rewrite-only API boundary. |
| Missing recipe artifact | `/private/tmp/ai-devkit/docs/standard/recipe-profile.md`, `README.md`, `server/src/server.py`, `server/src/agent.py`, `web/next.config.ts`, `web/src/services/api.ts` | `docs/ai/RECIPE.md`, `docs/ai/L0_repo_card.md`, `AGENTS.md` | Pass | Repo now declares `Recipe Role: base` and documents extension points, invariants, stable contracts, and internal surfaces. |
| Recipe lacked from-scratch guidance | `../agent-quickstart-nextjs/docs/ai/RECIPE.md`, `../agent-quickstart-nextjs/docs/ai/L1/L2/from_scratch_bootstrap.md`, local source files | `docs/ai/RECIPE.md`, `docs/ai/L1/L2/from_scratch_bootstrap.md`, `docs/ai/L1/L2/_index.md`, `docs/ai/L1/03_code_map.md`, `docs/ai/L1/05_workflows.md` | Pass | Python recipe now follows the Next.js recipe shape and links implementation detail from RECIPE/L1 into L2. |

## Verification Commands

| Command | Result | Notes |
| ------- | ------ | ----- |
| Structural docs checks | Pass | Required files exist; L1 files include purpose + `## Related Deep Dives`; L2 files include `When to Read This`. |
| `bun run verify:backend` | Pass | Required escalation because Python bytecode cache writes outside sandbox roots. |
| `bun run verify:web:api` | Pass | API contract checks passed. |
| `bun run verify:web:proxy` | Pass | Initial sandbox run could not bind local ports; rerun with escalation passed. |
| `bun run verify:web` | Blocked | Doctor and API checks passed after `bun install`; `next build` failed because restricted network could not fetch Google Fonts for `next/font`. |
