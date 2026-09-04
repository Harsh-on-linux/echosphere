# WeatherGPT — Manual Demo & Regression Script (plan.md 7.3 / 8.1)

Live-voice half of the test matrix. Automated half: `pytest server/tests`
(146+ tests, mock IMD, no cloud). Budget: this script burns ~5 Conv AI mins.

## Preconditions

- `bun run dev` green; `GET /health` shows `agora_configured: true`.
- `USE_MOCK_IMD=true` unless IMD whitelisting is approved (offline venue mode).
- Stopwatch + phone for the telephony-bridge row.

## Voice rows (speak, then check RTM history shows the tool chain)

| # | Say | Expect to hear (+ history shows) |
|---|-----|----------------------------------|
| 1 | "Pune me kal barish hogi kya sowing se pehle?" | Rain + sowing advice, Hindi; `resolve_location -> get_rainfall_stats + get_agromet_advisory` |
| 2 | "Is it safe to go to sea tomorrow from Rameswaram?" | Sea safety, Tamil/English; `resolve_location -> get_fishermen_warning + get_sea_area_bulletin` |
| 3 | "Cyclone track for Odisha?" | Position + MSW + cone; `get_cyclone_track + get_cyclone_wind`; map cone highlights while speaking |
| 4 | Start Q1, interrupt mid-answer: "Nahi, Nagpur ka batao" | Audio cuts <1s, answers Nagpur; `interrupt` then new `resolve_location` |
| 5 | Play traffic noise, ask Q1 again | Correct transcript (NS + SAL if voiceprint set) |
| 6 | "Weather in my small village Xyzzy?" | Single clarification ("Did you mean …?"), no loop |
| 7 | "Tell me in Tamil" mid-session | Voice switches, same IMD grounding |

## Edge rows

- **IMD outage:** set `IMD_API_URL=https://127.0.0.1:9`, `USE_MOCK_IMD=false`, restart
  backend, ask Q1 -> answers from last-cached data with timestamp ("last update …"),
  offers retry. Restore env after.
- **Cold-cache outage:** clear cache (`POST` nothing — restart backend), same setup ->
  answers from sample fallback marked busy, never a 500 to the caller.
- **Phone bridge:** call the demo laptop from a mobile on speaker, hold near the
  mic, run row 1 -> same loop, ~0 PSTN cost.

## Teardown (free-tier guard)

1. End Conversation in UI; `POST /stopAgent` if needed.
2. Agora Console > Usage: 0 active agents, session total <300 min overall.
3. Sarvam dashboard: still >Rs.50 after Indic rows.
4. Pre-call screen: Past Sessions lists this run (history + turns persisted).
