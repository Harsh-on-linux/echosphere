# WeatherGPT — Final Checks (plan.md 8.3)

## Local results (2026-09-04, this machine)

- [x] `agora project doctor` — green: session valid, rtc + rtm + convoai enabled, project ready for CONVOAI.
- [x] `pytest server/tests` — 152 passed (mock IMD, no cloud).
- [x] Offline mode ready: `data/sample_imd_responses/` has 4 samples
      (cityforecast_pune, districtnowcast_pune, fishermen_warning_nagapattinam,
      cyclonetrack_mock); `USE_MOCK_IMD=true` is the default.
- [x] Hygiene: `.env` + `server/.env` gitignored; tree clean before this file.

## Venue go/no-go (do live, in order)

- [ ] `agora project doctor` once more on venue network.
- [ ] Fresh browser, incognito: full flow per `docs/demo_narrative.md` 0:00–2:30.
- [ ] Same flow on mobile 4G (hotspot ok).
- [ ] Venue WiFi dead? Set `USE_MOCK_IMD=true`, restart backend, re-run 0:00 row.
- [ ] Record backup video after one clean live pass.
- [ ] Teardown: End Conversation, Agora Console > Usage shows 0 active agents,
      session total <300 min; Sarvam dashboard >Rs.50.

Related: `docs/demo_narrative.md`, `docs/judge_one_pager.md`,
`server/tests/manual_demo_script.md`.
