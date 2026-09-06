# VaayuMitra — 3-min Demo Narrative (plan.md 8.1)

One live voice session. Budget: ~3–5 Conv AI mins. Offline fallback: `USE_MOCK_IMD=true`.

## Preconditions

- `bun run dev` green; `GET /health` shows `agora_configured: true`.
- Pre-call Voice settings: ASR `hi-IN`, persona `farmer` (`web/src/components/VoiceSettingsPanel.tsx:5`).
- Stopwatch visible. Venue WiFi fallback: keep `USE_MOCK_IMD=true` unless IMD whitelisting approved.
- Greeting heard first (single_first, interruptable): `server/src/persona_prompt.py:30`.

## Run-of-show

| Time | Say (presenter) | Expect (voice + history shows) | Judge sees |
|------|-----------------|--------------------------------|------------|
| 0:00 | "VaayuMitra, Pune ka mausam?" (Hindi) | Greeting in Hindi, then short forecast | `VoiceOrb.tsx:16` listening → thinking → speaking; live transcript |
| 0:20 | Listen | Rain + sowing advice with IMD source + timestamp; `resolve_location -> get_rainfall_stats + get_agromet_advisory` | `IMDSourceCard.tsx:50` Tool/District/Updated; Mode `IMD live` or `IMD sample cache` |
| 0:40 | "Now as a fisherman, same place — can I fish?" | Same district, different routing: `resolve_location -> get_fishermen_warning + get_sea_area_bulletin` | Transcript shows sea-safety answer, color codes; proves persona routing (`server/src/persona_prompt.py:8`) |
| 1:10 | Mid-answer, interrupt: "Nahi, Nagpur ka batao" (or click Interrupt) | Audio cuts <1s, answers Nagpur; `interrupt` then new `resolve_location` | `InterruptButton.tsx:18` (`POST /interruptAgent`); VAD SoS interrupt (`server/src/agent.py:339`) |
| 1:30 | "Tell me in Tamil" | Same IMD grounding, Tamil TTS voice | Voice settings Sarvam `anushka` path (`VoiceSettingsPanel.tsx:13`); transcript in Tamil |
| 2:00 | Play boat-engine audio from phone, ask 0:00 line again | Correct transcript (built-in NS; SAL only if voiceprint set) | `AgentMetricsOverlay.tsx:27` latency vs 1200ms target; no transcript drift |
| 2:30 | Close (presenter, not voice): "IMD portal: 7 clicks, needs English. VaayuMitra: 7 sec voice, no literacy." | — | Point to transcript + IMD Source + metrics overlay on screen |

Tool names match MCP server: `server/src/mcp_server.py:8`.

## Fallback lines (say verbatim if anything fails)

- IMD slow: agent filler covers it — "Ek second, IMD check kar raha hun..." (`server/src/persona_prompt.py:91`).
- IMD down: agent answers from last-cached data with timestamp ("last update ..."), offers retry. Never a 500 to voice (`server/src/imd_client.py:84`).
- Ambiguous place: single clarification "Did you mean Thane or Thanjavur?", no loop (`server/src/persona_prompt.py:16`).
- No PSTN Beta: phone-bridge — call laptop from mobile on speaker by the mic, same loop, ~0 cost.

## Teardown (free-tier guard)

1. End Conversation in UI; `POST /stopAgent` if needed. `idle_timeout` 120s is backstop.
2. Agora Console > Usage: 0 active agents, session total <300 min.
3. Sarvam dashboard: still >Rs.50 after Indic rows.
4. Pre-call Past Sessions lists this run (history + turns persisted).

Related: full regression rows in `server/tests/manual_demo_script.md:1`; matrix automation in `server/tests/test_matrix.py:1`.
