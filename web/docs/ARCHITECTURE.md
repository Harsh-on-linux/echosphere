# Architecture

## 1. Tech Stack & Project Scope

- Project type: Next.js web app inside a Python-backed quickstart repo
- Frontend framework: Next.js 16 App Router + React 19
- Language: TypeScript
- Build tool: Next.js (`next dev --webpack`, `next build`)
- UI/Styling: Tailwind CSS
- State management: React component state; no Zustand store
- Data fetching: `web/src/services/api.ts` fetch helpers over `/api/*`
- SSR/Isomorphic: App Router shell with client conversation components

## 2. Package Management & Toolchain

- Runtime: Bun (latest stable)
- Package manager: bun
- Lint/Format: Biome
- Testing: custom bun verification scripts; no Vitest harness today
- CI/CD: Not defined in this repo
- Code generation: None

## 3. Runtime & Environment

- Environment variables: `AGENT_BACKEND_URL` for Next rewrites; backend secrets live under `server/`
- Required variables:
  - `AGENT_BACKEND_URL` - Python FastAPI backend URL for `/api/*` rewrites
  - `AGORA_APP_ID` and `AGORA_APP_CERTIFICATE` - server-side only, documented in `server/.env.example`
- Local/Test/Prod differences: root `bun run dev` exports `AGENT_BACKEND_URL=http://localhost:8000`; deploys must set it on the web host
- Entry point: `web/app/page.tsx` renders `LandingPage`
- Default port: 3000 for Next.js, 8000 for FastAPI
- Secrets handling: keep Agora certificate and BYOK keys out of `web/`

## 4. Dependencies & External Services

- Browser dependencies:
  - `agora-rtc-react` / `agora-rtc-sdk-ng` for RTC
  - `agora-rtm` for RTM
  - `agora-agent-client-toolkit` and `agora-agent-uikit` for transcript, state, metrics, and visualizer UI
- Backend service:
  - Python FastAPI owns token generation and agent lifecycle through `agora-agents`
- Third-party services: Agora Conversational AI managed STT/LLM/TTS pipeline

## 5. Module Responsibilities & Directory Structure

```
web/
├── app/
│   ├── layout.tsx      # metadata, font, global CSS
│   └── page.tsx        # renders LandingPage
├── src/
│   ├── components/     # conversation UI and primitives
│   ├── lib/            # Agora constants and transcript normalization
│   ├── services/       # API facade over /api/*
│   └── types/          # shared TypeScript contracts
├── scripts/            # doctor and verification harnesses
└── next.config.ts      # /api/* rewrites to FastAPI
```

## 6. Data Flow & Routing

- Routing: single App Router page at `/`
- Data flow:
  1. `LandingPage` calls `GET /api/get_config`
  2. Next rewrites to FastAPI `/get_config`
  3. Browser starts the agent via `POST /api/startAgent`, logs into RTM, and renders `ConversationComponent`
  4. `ConversationComponent` joins RTC, initializes `AgoraVoiceAI`, publishes the microphone, and renders transcript/state/metrics
  5. End call posts `/api/stopAgent`, logs out of RTM, and clears browser state
- Error handling: `ErrorBoundary`, `ConnectionStatusPanel`, and issue aggregation in `ConversationComponent`
- Loading states: `LoadingSkeleton` and pre-call loading state

## 7. Build & Deployment

- Build command: `bun run build`
- Output: `.next/`
- Deployment target: Next.js-compatible web host plus separately reachable FastAPI service
- Version strategy: conventional commits per root `AGENTS.md`
- Rollback: Redeploy previous version

## 8. Constraints & Known Issues

- Known constraints:
  - Agora SDK requires HTTPS in production
  - WebRTC requires user permission for microphone
  - `AGENT_BACKEND_URL` must be set for `/api/*` to work
- Known pitfalls:
  - Token expiration handling
  - Network reconnection logic
  - Do not add `web/app/api/**/route.ts`; this app intentionally uses rewrites only
- Behaviors that must not break:
  - Real-time audio streaming
  - RTM transcript and agent-state delivery
  - Browser-facing `/api/*` contract

## 9. Update Log

- 2026-05-28: Updated architecture for Next.js + Python FastAPI quickstart shape
