# WeatherGPT — Judge One-Pager (plan.md 8.2)

Voice-native IMD weather assistant for farmers, fishermen, disaster managers.
All voice flows through Agora Conversational AI Engine (SD-RTN + RTC/RTM + ASR→LLM→TTS).
Every weather fact carries IMD source + timestamp. 3-min live script: `docs/demo_narrative.md`.

## Try it

- Local: `bun run setup`, `bun run dev` → http://localhost:3000 → Start conversation.
- Prod target: backend `https://weathergpt-backend.onrender.com` (`render.yaml:24`),
  frontend on Vercel per `README.md:74`. Verify:
  `BACKEND_URL=https://weathergpt-backend.onrender.com bash scripts/verify-deploy.sh`.
- QR to live frontend: TODO — generate after Vercel deploy, print for the table.
  (Planned URL per `plan.md:336`: `weathergpt.vercel.app`; confirm before printing.)

## Architecture (SD-RTN central)

Diagram: `.github/images/system-architecture.svg`. Detail: `ARCHITECTURE.md:1`.

```
Mic → RTC → Agora Conv AI Engine (managed Deepgram nova-3 + gpt-4o-mini + MiniMax,
Sarvam BYOK for hi/ta/mr/bn-IN) → LLM calls POST {BACKEND_URL}/mcp tools → TTS → RTC
                                                                    ↳ RTM transcripts + state → UI
```

- Frontend only does token + channel + RTC (`ARCHITECTURE.md:19`). Tokens server-side.
- Agent lifecycle: `POST /startAgent` → session (`idle_timeout` 120s) → `POST /stopAgent`.
- Watch live: transcript, `IMDSourceCard`, metrics overlay (1200ms target), cyclone cone map.

## IMD grounding

Tools at `POST /mcp` (`server/src/mcp_server.py:8`): `resolve_location` first, then
`get_rainfall_stats` + `get_agromet_advisory` (farmer), `get_fishermen_warning` +
`get_sea_area_bulletin` (fisherman), `get_cyclone_track` + wind/cone (disaster).
Cache TTL 300s; outage serves last-good stale with timestamp, never a 500 to voice.

## Free-tier proof (from `research.md:337`)

| Item | Price | Free |
|------|-------|------|
| Conv AI Engine audio task (managed ASR/LLM/TTS incl.) | $0.10/min | first 300 min, one-time |
| Sarvam BYOK (Indic only) | STT ₹30/hr, TTS ₹15–30/10k chars | ₹100 credit, never expires |
| Cloud recording / extras | — | disabled, never enabled |

Budget: 300 min ≈ 100 demos × 3 min. Planned spend: dev 180 + rehearsal 50 + finale 25 = 255 < 300.
Guards: `idle_timeout` 120s, no card on file (suspends at 300 instead of charging), IMD cache 5 min.

## Impact

- IMD portal today: ~7 clicks, English text, needs literacy + data. WeatherGPT: ~7 sec voice, no literacy needed.
- Telephony-first: feature-phone farmer dials in (Beta via Console → Talk to Us); today the
  phone-bridge fallback (mobile on speaker by laptop mic) demos the same loop at ~0 cost.
- Population-scale impact numbers: TODO — fill with sourced figures before printing.

## If venue network fails

1. `USE_MOCK_IMD=true` (sample IMD cache, offline mode) + `docs/demo_narrative.md` fallbacks.
2. Backup video recording of the 3-min run: TODO — record after one clean live pass.
3. End every run in UI; confirm 0 active agents (free-tier guard).
