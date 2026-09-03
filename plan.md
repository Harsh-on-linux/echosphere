# WeatherGPT — Step-by-Step Implementation Plan
> Voice-native IMD assistant | Agora Conversational AI Engine as CENTRAL layer | Free-tier first
> Stack: Agora RTC+RTM+Conv AI Engine + FastMCP + IMD APIs + Sarvam (Indic) | Templates: Python or Next.js

---

## Overview & Success Criteria

**What judges score:** AI integration (how well Agora is used), functionality (real voice, interruptions, multilingual, tool calling), impact (rural accessibility via telephony + IMD grounding).

**Success for finale (Delhi live):**
- 3-min demo: user speaks Hindi/Tamil/Marathi or English -> agent resolves district -> calls correct IMD API -> responds in same language vocally -> handles interruption + follow-up.
- No hallucinated numbers; every weather fact has IMD `source + timestamp`.
- Works on web (laptop) and on paper, would work on phone call (PSTN simulated).

**Free budget:** <300 Conv AI mins total during dev + demo. Managed LLM/TTS + Sarvam ₹100 free for Indic.

---

## Phase 0 — Foundations (Day 0, 2-3 hours)

### Step 0.1 — Create Accounts & Enable Services
1.  Create Agora account at https://sso.agora.io/en/signup -> create project in Console -> note `App ID`, `App Certificate`, `Customer ID`, `Customer Secret` (REST auth). Verify Conversational AI Engine is Enabled (new projects: enabled by default, RTC Services page).
2.  Create Sarvam account at https://dashboard.sarvam.ai -> generate `API Key` -> verify ₹100 credit appears. Save `SARVAM_API_KEY`.
3.  Create OpenAI account (optional fallback) -> generate key if you want BYOK test later; for hackathon prefer managed (no key).
4.  Request IMD IP whitelisting at https://api.imd.gov.in/public/index.php -> enter public IP + email -> wait for approval (can take 24h; start Day 0). Meanwhile use cached sample JSON to unblock dev.
5.  Contact Agora support via Console > Talk to Us to request **Telephony Beta** access (outbound/inbound). Mention hackathon SIH26068 — even if denied, you can mock.

**Deliverable:** `.env` keys file. **Verification:** `agora project doctor` later passes.

### Step 0.2 — Install Tooling
1.  Install Agora CLI (Windows):
    ```powershell
    irm https://dl.agora.io/cli/install.ps1 | iex
    agora --help
    agora login
    ```
2.  Install Node `bun` (starter uses it), `pnpm`, `python 3.10+`, `poetry` or `pip`.
3.  Install `npx skills add AgoraIO/skills` + add MCP server `https://mcp.agora.io` to your IDE (Cursor/Claude) — lets AI check live docs.
4.  Clone skill references: `AgoraIO/skills` for prompts.

**Deliverable:** `agora --version` + `bun --version` works.

### Step 0.3 — Choose Template & Init Project
Decision:
- **Python** if team is python-heavy, easy IMD parsing + FastMCP co-located.
- **Next.js (TypeScript)** if you need fancy map UI for judges.

Command:
```bash
agora init weathergpt --template python   # or nextjs
cd weathergpt
bun run setup
bun run dev   # should open http://localhost:3000 with Start conversation button
```

**Test without changes:** Click Start conversation, say hello -> agent replies via managed `gpt-4o-mini + MiniMax`. Check console + RTM transcripts.

**Verification:** If fails: `agora project doctor` + check `idle_timeout` + `customerId:secret` base64.

---

## Phase 1 — Project Scaffolding & Structure (Day 0-1, 3 hours)

### Step 1.1 — Define Folder Layout
```
weathergpt/
├── frontend/                # from starter (Next.js or Vite)
│   ├── src/ components/ VoiceClient.tsx, MapPanel.tsx, Transcript.tsx
│   └── pages/api/token.ts, start-agent.ts, stop-agent.ts
├── backend/                 # Python FastAPI or Node
│   ├── main.py              # FastAPI app + MCP server
│   ├── mcp_server.py        # FastMCP IMD tools
│   ├── imd_client.py        # IMD API wrappers + caching
│   ├── location_resolver.py # fuzzy district resolver + shapefile
│   ├── persona_prompt.py    # system prompts per persona
│   └── requirements.txt
├── data/
│   ├── imd_districts.json   # district_id -> name, state, coastal flag
│   ├── imd_stations.json
│   └── sample_imd_responses/ # cached JSON for offline dev
├── research.md              # this file compiled
├── plan.md                  # this plan
└── .env
```

### Step 1.2 — Create Backend Skeleton
1.  `backend/main.py` — FastAPI with CORS, `/health`, `/api/token` (generates RTC token via `agora_token_builder` or SDK).
2.  `backend/imd_client.py` — functions per endpoint, shared `httpx` client, 5 min TTL cache (`cachetools.TTLCache` or Redis if deployed).
3.  `backend/location_resolver.py` — load `imd_districts.json`, use `rapidfuzz` to map `"Thane"` or `"Chennai area"` -> `district_id`. Handle Marathi/Tamil transliteration via simple mapping table first.
4.  `backend/mcp_server.py` — FastMCP server exposing tools (see Phase 3).
5.  Add `spatial reasoning`: if district not found, return nearest 3 districts + latlon fallback to `cityforecast?lat=&lon=`.

**Verification:** `pytest backend/tests/` mocking IMD with sample JSON passes.

### Step 1.3 — Token Server & Env Wiring
- Generate RTC token: `RtcTokenBuilder.buildTokenWithUid(appId, appCert, channel, uid, role, expiry 3600)` + RTM token similarly.
- Endpoint: `POST /api/token {channel, uid}` -> returns `{rtcToken, rtmToken}`.
- Ensure frontend passes `agent_rtc_uid: "0"` (reserved) + `remote_rtc_uids: ["*"]` to listen to any user.

**Deliverable:** `curl http://localhost:8000/api/token -d '{"channel":"test"}'` returns tokens.

---

## Phase 2 — Core Voice Loop — Get Audio Flowing (Day 1, 4 hours)

### Step 2.1 — Connect Managed Pipeline First (English, cheapest)
Goal: Prove Agora is central before adding complexity.

In `backend/main.py` create `POST /api/start-agent`:
```python
from agora_agent import Agent, Agora, Area
from agora_agent.agentkit import DeepgramSTT, OpenAI, MiniMaxTTS

client = Agora(area=Area.US, app_id=APP_ID, app_certificate=APP_CERT)
agent = Agent(client, turn_detection={"language":"en-US"}).with_stt(DeepgramSTT(model="nova-3", language="en")).with_llm(OpenAI(model="gpt-4o-mini", system_messages=[...], greeting_message="Hello, I am WeatherGPT. Which district?", max_history=10)).with_tts(MiniMaxTTS(model="speech-2.6-turbo", voice_id="English_captivating_female1"))
session = agent.create_session(channel=channel, agent_uid="0", remote_uids=["*"], name=f"wx-{int(time.time())}", idle_timeout=120)
agent_id = session.start()
```

**Verification:** Frontend `Start conversation` -> speak "What is weather in Pune?" -> transcript appears via RTM -> agent replies in English -> audio plays. Check `GET /agents/{id}/turns` for latency <1s.

### Step 2.2 — Add Front-End Voice UI (Proves 6 Features Visually)
1.  Components:
    - `VoiceOrb` — pulses on `listening/thinking/speaking` states from RTM `state.*` events (v2.9).
    - `LiveTranscript` — uses `SubtitleManager` pattern from playground blog (coalesce interim ASR).
    - `IMDSourceCard` — shows last tool called, district resolved, API timestamp.
    - `InterruptButton` — calls `POST /agents/{id}/interrupt` for manual interrupt demo.
2.  Settings panel: dropdown to switch `ASR language` / `TTS voice` without restarting channel (demonstrates Any model/voice).

**Deliverable:** Screen recording of natural conversation with visible state.

### Step 2.3 — Implement Leave & Error Handling
1.  `POST /api/stop-agent {agentId}` -> `session.stop()` -> user leaves channel.
2.  Handle `idle_timeout` — auto leave after 2 min silence (saves free mins).
3.  Show `failure_message` when LLM cannot answer or IMD fails: "IMD data busy, last update ...".

**Verification:** No idle burn; `agora project doctor` shows no lingering agents.

---

## Phase 3 — IMD Tool Layer — Make Data Real (Day 1-2, 6 hours)

### Step 3.1 — Build IMD Client with Real Endpoints
Implement wrappers (async httpx) for each URL from research.md #11. Example:
```python
async def get_district_nowcast(district_id: str):
  url = f"https://api.imd.gov.in/api/v1/districtnowcast?id={district_id}"
  headers = {"Authorization":"Bearer ..."} # if needed after whitelisting
  cached = cache.get(url)
  if cached: return cached
  resp = await client.get(url, timeout=5)
  data = resp.json()
  cache.set(url, data, ttl=300)
  return data
```
Add retries with backoff, attribution header.

**Testing:** Without whitelisting, use `sample_imd_responses/` and feature flag `USE_MOCK_IMD=true`.

### Step 3.2 — Expose via FastMCP
```python
from fastmcp import FastMCP
mcp = FastMCP("imd-mcp")

@mcp.tool()
async def resolve_location(location_text: str) -> dict:
  """Resolve spoken place to IMD district_id. Use before any weather tool."""
  return location_resolver.fuzzy_match(location_text)

@mcp.tool()
async def get_city_forecast_7d(district_id: str) -> dict:
  return await imd_client.get_city_forecast(district_id)

@mcp.tool()
async def get_fishermen_warning(district_id: str) -> dict:
  return await imd_client.get_fishermen_warning(district_id)
# ... 7 more tools

# Mount at /mcp for Agora to call
app.mount("/mcp", mcp.sse_app())
```
**Verification:** `curl https://your-backend/mcp -d '{"method":"tools/list"}'` lists tools. Test locally with MCP inspector.

### Step 3.3 — Wire MCP to Agent
Update `Agent` creation to:
```python
.with_llm(OpenAI(
  model="gpt-4o-mini",
  system_messages=[WEATHERGPT_SYSTEM],
  mcp_servers=[{"url": f"{BACKEND_URL}/mcp", "name": "imd"}]
))
# + advanced_features.enable_tools=true
```
System prompt must enforce:
```
You are WeatherGPT, IMD-grounded. Steps: 1) Detect persona (farmer asks rain/sowing, fisherman asks sea, officer asks cyclone). 2) Call resolve_location. 3) Call ONE IMD tool relevant to persona. 4) Summarize in user's language, <30 words, plain, with source. 5) Never hallucinate numbers.
```

**Verification:** Say "Is it safe to go fishing from Nagapattinam tomorrow?" -> RTM history shows `resolve_location("Nagapattinam") -> get_fishermen_warning` -> spoken answer references IMD warning.

### Step 3.4 — Add Spatial Reasoning & Fallbacks
1.  If `resolve_location` confidence <70, ask clarification: "Did you mean Thane or Thanjavur?"
2.  If district data null, try lat/lon via `cityforecast?lat=&lon=` using cached geocode (Nominatim free).
3.  For state-wide queries, call `subdivisionwarning` and summarize.

**Deliverable:** Table test across 10 informal names (Mumbai, Bombay, Mum-bai, Thane Creek) resolves correctly.

---

## Phase 4 — Multilingual & Persona-Aware (Day 2, 5 hours)

### Step 4.1 — Enable Indic Pipeline (BYOK Sarvam)
Create language map:
```python
LANG_CONFIG = {
  "en-IN": {"asr": SarvamSTT(language="en-IN"), "tts": SarvamTTS(speaker="anushka", target_language_code="en-IN")},
  "hi-IN": {"asr": SarvamSTT(language="hi-IN"), "tts": SarvamTTS(speaker="anushka", target_language_code="hi-IN")},
  "ta-IN": {...}, "mr-IN": {...}, "bn-IN": {...}
}
```
Detection: Use `asr.language="unknown"` for auto-detect, or ask user at start "Aap kaun si bhasha?" and set `turn_detection.language` accordingly.

**Free check:** Sarvam ₹100 covers ~50-60 full dialogues; monitor dashboard usage after each test.

### Step 4.2 — Persona-Aware Prompt + Tool Routing
Enhance system prompt with persona logic:
- If user says `fisherman, sea, boat, machli` -> prioritize `fishermen_warning + sea_area_bulletin + coastal_bulletin`.
- If `farmer, crop, sowing, barish` -> `rainfall + agromet + district_forecast`.
- If `cyclone, storm, tamil nadu coast` -> `cyclone_track + wind_warning`.

Add `TTS pace`: slower (0.9) for elders, `pitch` tweak per persona.

**Verification:** Same location "Mumbai" -> farmer gets rain forecast, fisherman gets sea warning (show judges side-by-side).

### Step 4.3 — Greeting & Filler Polish
```json
"llm": {"greeting_message": "Namaste, main WeatherGPT hun...", "greeting_configs": {"mode":"single_first", "interruptable": true, "delay_ms": 200}},
"filler_words": {"enable": true, "words": ["Ek second, IMD check kar raha hun..."]}
```
If deploying telugu/tamil greeting audio pre-recorded, use `greeting_audio_url` (v2.9).

**Deliverable:** Seamless first 3 seconds — user hears greeting without TTS lag.

---

## Phase 5 — Conversation Quality & The 6 Features Demo (Day 2-3, 4 hours)

### Step 5.1 — Turn Detection & Interruption Tuning
Config:
```json
"turn_detection": {"mode":"default","config":{"start_of_speech":{"mode":"vad","vad_config":{"interrupt_threshold":0.5,"prefix_padding_ms":250}},"end_of_speech":{"mode":"vad","vad_config":{"silence_duration_ms":700}}}},
"interruption": {"enable":true,"mode":"start_of_speech"}
```
Test:
- Quiet room: lower `threshold` to 0.4.
- Noisy: raise to 0.7 + enable SAL.

Prove: Record video showing agent speaking, judge says "Ruko!" -> audio cuts within 300ms. Also test `interrupt()` button for manual.

### Step 5.2 — Noise Suppression & SAL Setup
- For fisherman demo: collect 10 sec voiceprint `sal_sample.wav` per persona, host at public URL, pass to `sal.sample_urls`. Enable `advanced_features.enable_sal=true`.
- Test with YouTube boat engine sound playing in background — ASR accuracy should stay >90%.

**Verification:** Toggle SAL off/on and show transcript diff.

### Step 5.3 — Optimize Latency & State UI
- Set `parameters.enable_metrics=true` + `enable_rtm=true` -> listen to `onAgentListeningChanged/ThinkingChanged/SpeakingChanged` to drive orb colors.
- Log `111 agent metrics` latency per turn; target <1200ms total (ASR 300 + LLM 400 + TTS 300).

**Deliverable:** Metrics overlay on screen for judges.

---

## Phase 6 — Hosting, Persistence & Telephony (Day 3, 3 hours)

### Step 6.1 — Deploy
- Backend: Render Free / Fly.io / Railway -> set `BACKEND_URL` env. Ensure `/mcp` is public HTTPS (Agora requires https for MCP).
- Frontend: Vercel Hobby -> env `NEXT_PUBLIC_BACKEND_URL`.
- Use single Agora project; share `APP_ID` across envs via `agora init` env file.

### Step 6.2 — Add Persistence & History
- Store `GET /agents/{id}/history` + `GET /turns` to local storage or cheap Supabase free tier for post-demo analytics.
- Show map: when agent says "cyclone cone", frontend draws GeoJSON from `cyclonewind` MultiPolygon on Leaflet map in real-time (sync to voice state `speaking`).

### Step 6.3 — Telephony Mock (if Beta not granted)
- Fallback: Use Twilio SIP trunk -> forward call to Agora channel via `media push` or simply demo "phone call" by calling from mobile to laptop mic and holding phone up — still proves telephony-first concept without PSTN cost.
- If Beta granted: implement `POST /dial` flow; test with your own number.

**Verification:** `curl` deployed backend health + one full voice session via production URL works.

---

## Phase 7 — Testing, QA & Free-Tier Guardrails (Day 3, 3 hours)

### Step 7.1 — Cost Guard Tests
1.  Simulate 10 idle agents -> ensure `idle_timeout` kills them; monitor `agora console > usage`.
2.  Verify no card added — after 300 min, Agora suspends instead of charging (desired).
3.  Check Sarvam dashboard after 20 Indic sessions — still >₹50 left?
4.  Cache hit rate: IMD calls should be <30% of queries after warmup.

### Step 7.2 — Functional Test Matrix
| Test | Input (voice) | Expected IMD Tool | Language |
|------|---------------|-------------------|----------|
| Farmer Maharashtra | "Pune me kal barish hogi kya sowing se pehle?" | `resolve+get_rainfall+agromet` | hi-IN |
| Fisherman TN | "Is it safe to go to sea tomorrow from Rameswaram?" | `resolve+fishermen_warning+sea_bulletin` | ta-IN |
| Disaster | "Cyclone track for Odisha?" | `cyclone_track+wind` | en-IN |
| Interrupt | Start forecast then "Nahi, Nagpur ka batao" mid-speech | Interrupt + new tool call | hi-IN |
| Noise | Play traffic sound, ask weather | Correct transcription | en-IN |
| Invalid place | "My small village X" | Clarify + nearest district | en-IN |

**Automation:** Record audio fixtures, play via `ffmpeg` to RTC channel for regression.

### Step 7.3 — Edge Cases
- IMD API down/timeout -> respond with last cached + timestamp, offer retry.
- Location ambiguous -> ask single clarification, not loop.
- Rate limit (IMD 20 PCU) -> queue + backoff + user filler: "Thoda samay dijiye".

**Deliverable:** `tests/` passing, `tests/manual_demo_script.md`.

---

## Phase 8 — Demo Script & Judging Optimization (Day 3-4, 2 hours)

### Step 8.1 — Build Demo Narrative (3 min live)
0:00 Greeting in Hindi: "WeatherGPT, Pune ka mausam?"
0:20 Agent answers with IMD source.
0:40 Switch persona live: "Now act as fisherman, same place — can I fish?" -> shows tool routing diff.
1:10 Interrupt mid-answer: proves intelligent interruption.
1:30 Language switch: "Tell me in Tamil" -> agent switches voice mid-session.
2:00 Noisy demo: play boat sound, show correct result vs without SAL.
2:30 Impact slide: "IMD portal: 7 clicks, needs English. WeatherGPT: 7 sec voice, no literacy."

### Step 8.2 — Materials for Judges
- One-pager with architecture diagram (SD-RTN central), free tier proof (cost sheet), impact numbers (farmers/fishermen population).
- QR -> live `weathergpt.vercel.app` for judges to try.
- Backup video recording in case network fails.

### Step 8.3 — Final Checks
- Run `agora project doctor` one last time.
- Fresh browser, incognito, test full flow on mobile 4G.
- Have `sample_imd_responses` offline mode toggle if venue WiFi fails.

---

## Timeline Summary

| Day | Phase | Hours | Milestone |
|-----|-------|-------|-----------|
| 0 | 0 Foundations | 3 | Keys + CLI + mock voice loop works |
| 0-1 | 1 Scaffolding | 3 | Repo, token server, resolver skeleton |
| 1 | 2 Core voice | 4 | English managed voice loop live |
| 1-2 | 3 IMD tools | 6 | MCP + 10 tools + caching |
| 2 | 4 Multilingual | 5 | Sarvam Indic + persona routing |
| 2-3 | 5 Quality | 4 | Interruption, SAL, metrics UI |
| 3 | 6 Deploy | 3 | Render/Vercel live + map sync |
| 3 | 7 QA | 3 | Test matrix + free guard |
| 3-4 | 8 Demo | 2 | Script + recording |

**Total: ~33 hours solo — feasible in 4-day hackathon sprint with 2 people parallelizing frontend/backend.**

---

## Dependencies & Risk Mitigation

- **IMD Whitelisting delay:** Start with mock JSON, switch to live when approved — no blocker.
- **Sarvam credits:** Monitor daily; if low, fallback to managed English for most tests, save Indic for finale.
- **Telephony Beta not granted:** Web demo is sufficient; pitch phone number as `Beta requested` — judges value telephony-first design even if mock.
- **Agora 20 PCU limit:** Use one channel per demo, leave immediately; queue if needed.

---

## File Checklist

- [ ] `research.md` (this repo) — all Agora + IMD + pricing research
- [ ] `.env` with `APP_ID`, `APP_CERTIFICATE`, `CUSTOMER_ID`, `CUSTOMER_SECRET`, `SARVAM_API_KEY`, `BACKEND_URL`
- [ ] `backend/mcp_server.py` with 10 tools
- [ ] `backend/imd_client.py` with caching
- [ ] `frontend/VoiceClient.tsx` with RTC+RTM
- [ ] `agora project doctor` green
- [ ] Deployment URLs + Demo video

> Next action: Choose template (`python` or `nextjs`) and run `agora init` — then scaffold `backend/mcp_server.py` per Phase 3.
