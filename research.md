# VaayuMitra — Research Compilation
> Conversational AI for Weather Forecasting, Alerts, and Climate Information (SIH26068) + Agora Conversational AI Hackathon — EchoSphere
> Generated: 2026-09-03
> Project: VaayuMitra — voice-native, multilingual IMD data assistant for farmers, fishermen, disaster managers

---

## Table of Contents
1. [Agora Conversational AI Engine — Core Research](#1-agora-conversational-ai-engine--core-research)
2. [The 6 Main Features (from product image)](#2-the-6-main-features-from-product-image)
3. [Architecture — How Agora Works](#3-architecture--how-agora-works)
4. [Integration Paths — CLI / SDK / REST](#4-integration-paths--cli--sdk--rest)
5. [Model Ecosystem — ASR / LLM / TTS / Avatars](#5-model-ecosystem--asr--llm--tts--avatars)
6. [Tool Calling & MCP — Connecting IMD Data](#6-tool-calling--mcp--connecting-imd-data)
7. [Turn Detection, Interruption & Conversation Control](#7-turn-detection-interruption--conversation-control)
8. [Noise Suppression & Selective Attention Locking](#8-noise-suppression--selective-attention-locking)
9. [Telephony (PSTN) & Device Kit](#9-telephony-pstn--device-kit)
10. [Pricing & Free-Tier Strategy](#10-pricing--free-tier-strategy)
11. [IMD — India Meteorological Department APIs](#11-imd--india-meteorological-department-apis)
12. [Indic Language Stack — Sarvam AI](#12-indic-language-stack--sarvam-ai)
13. [LLM & STT/TTS Provider Pricing](#13-llm--stttts-provider-pricing)
14. [Observability, Security & Limits](#14-observability-security--limits)
15. [Sources & Official Docs](#15-sources--official-docs)

---

## 1. Agora Conversational AI Engine — Core Research

**What it is:** Unified orchestration layer on top of Agora's global Software-Defined Real-Time Network (SD-RTN®) that connects `ASR -> LLM -> TTS` with real-time transport, interruption handling, and agent lifecycle control. Not a TTS wrapper; Agora owns the audio path and coordination.

**Product Paths (docs.agora.io/en/introduction/conversational-ai):**
- **Conversational AI Engine** — Main path for real-time voice agents with managed speech, reasoning, interruption handling, lifecycle control.
- **AI Developer Toolkits** — Client/server surfaces for web, mobile, backend (RTC SDK + RTM/Singaling + Toolkits).
- **OpenAI Realtime** — Guided path for OpenAI Realtime-style flows over Agora transport.

**Key Characteristics (Agora Docs):**
- Ultra-low latency — responsive turn-taking vs chatbot.
- Voice-native interaction — combines RTC, ASR, LLM, TTS, interruption, lifecycle in one model.
- Flexible model strategy — managed keys or BYOK; any LLM.

**Current Version:** v2.11 (Aug 11, 2026) — see Release Notes `/en/ai/release-notes`. Key recent additions:
- v2.11: ASR keywords, Typecast TTS, Azure OpenAI Realtime MLLM, improved long audio stability.
- v2.10: Generic TTS via OpenAI protocol, manual turn control via client toolkits, Gradium/Mistral TTS.
- v2.9: Manual turn control (manual SoS/EoS), RTM state notifications, pre-recorded greeting audio, managed mode.
- v2.7: xAI Grok MLLM, generic avatar, greeting interruption control.
- v2.6: `POST /think` custom instruction, MLLM turn detection refactor, unified `interruption` object, agent state callbacks.
- v2.4: MCP integration (`llm.mcp_servers`), filler phrases, turn detection optimization.

**Supported Platforms:** Web, Android, iOS, Windows, macOS, Unity, Flutter, React Native, Electron, Unreal.

**playground:** https://conversational-ai.agora.io — test LLM/TTS/VAD without code.
**Console:** https://console.agora.io/v2

---

## 2. The 6 Main Features (from product image)

| # | Feature | What Agora Does | Config / Where |
|---|---------|-----------------|----------------|
| 1 | **Any AI model, any voice** | Connect any LLM + any ASR + any TTS. Cascade model `STT->LLM->TTS` is fully swappable. | `properties.asr.vendor`, `properties.llm.vendor`, `properties.tts.vendor` in `POST /join` |
| 2 | **Interactive AI avatars** | Akool (Beta), HeyGen (Alpha/LiveAvatar), Anam, Generic, LemonSlice — lip-synced to TTS. | `properties.avatar` — only with cascade pipeline, not MLLM |
| 3 | **Reduced response delay** | Ultra-low latency via SD-RTN, 3x faster than major LLM voice mode. Global intelligent routing, packet loss recovery. | Automatic — no config. Enhanced by `filler_words` |
| 4 | **Intelligent interruption handling** | Advanced acoustic algorithm detects user voice and stops agent TTS immediately. Voice + manual (button) interruption. | `properties.interruption.mode = start_of_speech / keywords`, `turn_detection` |
| 5 | **Background noise suppression** | Built-in noise suppression + echo cancellation blocks background voices/noise. | Automatic — always on. Tunable via `audio` params |
| 6 | **Selective attention locking** | Voiceprint-based speaker tracking; ignore background distractions. Essential for group/shared spaces. | `advanced_features.enable_sal + sal.sal_mode + sal.sample_urls` (Beta) |

> All 6 are included in Conversational AI Engine $0.10/min. No add-on fee. Verified from pricing page and product page https://www.agora.io/en/products/conversational-ai-engine/

---

## 3. Architecture — How Agora Works

**Four Layers (docs.agora.io/en/ai):**
1.  **Real-time transport:** SD-RTN moves audio, events, state between user and agent.
2.  **Agent runtime:** Manages session lifecycle, turn taking, interruptions, memory (`max_history`), tool orchestration.
3.  **Models:** ASR, LLM, TTS, optional MLLM/Avatar.
4.  **Endpoint:** App (web/mobile/backend) or dedicated device (toy/wearable/kiosk).

**Chained Pipeline:**
```
User mic (RTC) -> ASR (text) -> LLM (reason + tool calls) -> TTS (audio) -> RTC back to user
                                  |-> MCP Server -> IMD APIs
                                  |-> RTM -> transcripts / state (listening/thinking/speaking)
```

**Workflow (docs.agora.io/en/ai/build/start-stop-agent):**
1. User joins Agora channel (RTC + RTM token).
2. Business server calls `POST /v2/projects/{appid}/join` to create agent. Agent joins same channel.
3. Real-time voice interaction via SD-RTN.
4. Business server calls `POST /agents/{agentId}/leave` to stop. User leaves channel.

**Components in Starter:**
- Browser app: captures mic, plays agent audio (RTC SDK).
- Server controls: generates tokens, start/stop agent.
- Agora: transports low-latency audio + session events.

**Core Concepts:** RTC channels, UIDs, tokens, Signaling (RTM) for data channel.

---

## 4. Integration Paths — CLI / SDK / REST

### 4.1 Agora CLI (Fastest, 5 min)
Native Go binary at `github.com/AgoraIO-Community/cli`
```bash
# Windows PowerShell
irm https://dl.agora.io/cli/install.ps1 | iex
agora --help
# macOS/Linux
curl -fsSL https://dl.agora.io/cli/install.sh | sh
```
Flow:
```bash
agora login
agora init my-python-demo --template python   # or nextjs / go
cd my-python-demo
bun run setup      # sets up web client + backend
bun run dev        # http://localhost:3000 -> Start conversation
agora project doctor  # checks credentials, feature enablement, network
```
Starter repos:
- `AgoraIO-Conversational-AI/agent-quickstart-python`
- `AgoraIO-Conversational-AI/agent-quickstart-nextjs`
- `AgoraIO-Conversational-AI/agent-quickstart-go`

Environments written to `.env` by CLI: `APP_ID`, `APP_CERTIFICATE`, `CUSTOMER_ID`, `CUSTOMER_SECRET`.

### 4.2 Agents SDK (Typed Builders)
**Install:**
```bash
pip install agora-agents      # python: from agora_agent import Agent, Agora, Area
npm install agora-agents      # typescript: import { Agent, AgoraClient } from 'agora-agents'
go get github.com/AgoraIO/agora-agents-go/v2@v2.2.0
```
**SDK sits on top of REST — handles:** typed pipeline builders, dynamic token generation, session lifecycle (`create_session/start/stop/query`).

**Python Quick Start (Managed Mode — no keys needed):**
```python
from agora_agent import Agent, Agora, Area
from agora_agent.agentkit import DeepgramSTT, OpenAI, MiniMaxTTS

client = Agora(area=Area.US, app_id='your-app-id', app_certificate='your-app-certificate')
agent = (
    Agent(client, turn_detection={"language": "en-US"})
    .with_stt(DeepgramSTT(model='nova-3', language='en'))
    .with_llm(OpenAI(
        model='gpt-4o-mini',
        system_messages=[{'role':'system','content':'You are a helpful chatbot.'}],
        greeting_message='Hello, how can I help you?',
        failure_message="Sorry, I don't know.",
        max_history=10,
    ))
    .with_tts(MiniMaxTTS(model='speech-2.6-turbo', voice_id='English_captivating_female1'))
)
session = agent.create_session(channel='your_channel', agent_uid='0', remote_uids=['1002'], name='unique', idle_timeout=120)
agent_id = session.start()
# session.stop()
```

**Key SDK Detail:** `turnDetection.language` sets ASR language for ARES. Provider-specific `asr.params.language` still needed for others.

### 4.3 REST API Direct
**Host:** `https://api.agora.io/api/conversational-ai-agent`
**Base URL:** `https://api.agora.io/api/conversational-ai-agent/v2/projects/{appid}`
**Auth:** `Authorization: Basic base64(customerId:customerSecret)` + `Content-Type: application/json`
**Endpoints:**
- `POST /join` — start agent (name + properties)
- `POST /agents/{agentId}/leave` — stop (async)
- `POST /agents/{agentId}/update` — update RTC token
- `GET /agents/{agentId}` — query status
- `GET /agents` — list
- `POST /agents/{agentId}/think` — inject custom instruction (v2.6)
- `POST /agents/{agentId}/interrupt` — manual interrupt
- `GET /agents/{agentId}/history` — conversation history
- `GET /agents/{agentId}/turns?page_index& page_size` — per-turn latency metrics

**Join Payload Key Fields:**
```json
{
  "name": "unique_name",
  "properties": {
    "channel": "my_channel",
    "token": "rtc_token",
    "agent_rtc_uid": "0",
    "remote_rtc_uids": ["*"],
    "idle_timeout": 120,
    "asr": {"vendor":"deepgram", "params":{"model":"nova-3","language":"en"}, "credential_mode":"managed"},
    "llm": {"vendor":"openai", "params":{"model":"gpt-4o-mini"}, "system_messages": [...], "greeting_message":"...", "max_history":10},
    "tts": {"vendor":"minimax", "params":{"model":"speech-2.6-turbo","voice_id":"..."}},
    "turn_detection": {"mode":"default","config":{"end_of_speech":{"mode":"vad"}}},
    "interruption": {"enable":true,"mode":"start_of_speech"},
    "advanced_features": {"enable_tools":true, "enable_rtm":true},
    "mcp_servers": [{"url":"https://.../mcp"}],
    "parameters": {"data_channel":"rtm", "enable_metrics":true}
  }
}
```

**Limits:** 20 peak concurrent users (PCU) per App ID for server API; 72 hours max session despite `idle_timeout=0`; `idle_timeout` range 0-259200 secs.

---

## 5. Model Ecosystem — ASR / LLM / TTS / Avatars

### ASR Providers
- **Managed (in $0.10):** ARES (36 languages, default), Deepgram nova-2 / nova-3 (50+ languages)
- **BYOK:** Microsoft Azure (100+ langs), Deepgram, Sarvam (hi-IN, ta-IN, te-IN, bn-IN, kn-IN, ml-IN, mr-IN, gu-IN, pa-IN, or-IN, bn-IN, en-IN, `unknown` auto), OpenAI Whisper, Speechmatics, Google, Amazon Transcribe, AssemblyAI, xAI, etc.

**Sarvam BYOK Example:**
```json
"asr": {"vendor":"sarvam", "language":"unknown", "params":{"api_key":"SARVAM_KEY","language":"hi-IN"}}
```

### LLM Providers
- **Managed:** OpenAI `gpt-4o-mini`, `gpt-4.1-mini`, `gpt-5-nano`, `gpt-5-mini`
- **BYOK:** OpenAI, Azure OpenAI, Google Gemini / Vertex AI, Anthropic Claude, Groq, Amazon Bedrock, Dify, Custom LLM (any HTTP endpoint), xAI Grok

**Custom LLM:** Provide `url` to your `POST /chat/completions` server; Agora forwards conversation and streams SSE chunks. Field `metadata.interruptable` in first SSE chunk controls if TTS can be interrupted.

### TTS Providers
- **Managed:** MiniMax `speech-2.6-turbo` / `2.8-turbo`, OpenAI `tts-1`
- **BYOK:** Microsoft Azure, ElevenLabs, OpenAI, Cartesia, Hume AI, Sarvam (11 languages, voices: anushka/manisha/vidya/arya/abhilash/karun/hitesh), Rime, Fish Audio, Google, Amazon Polly, Deepgram, Murf, Gradium, Mistral, Typecast, Generic HTTP (OpenAI protocol)

**Sarvam TTS Example:**
```json
"tts": {"vendor":"sarvam","params":{"api_subscription_key":"SARVAM_KEY","speaker":"anushka","target_language_code":"ta-IN","pace":1.0}}
```

### MLLM (Voice-to-Voice)
- OpenAI Realtime API, Google Gemini Live, Azure OpenAI Realtime, xAI Grok — use `mllm` block with `enable:true`, `turn_detection` inside MLLM.

### Avatars
- Akool Beta, HeyGen LiveAvatar Beta, Anam Beta, LemonSlice, Generic Avatar Beta — only with cascade `ASR+LLM+TTS`, not MLLM. Disable with `enable:false` if testing MLLM.

---

## 6. Tool Calling & MCP — Connecting IMD Data

**Two Options:**

**A. MCP (Recommended — v2.4+):**
- Set `advanced_features.enable_tools=true` + `llm.mcp_servers: [{url:"https://your-backend/mcp"}]`
- LLM decides to call MCP tool -> Agora sends JSON-RPC to your FastMCP server -> returns result -> LLM speaks it.
- Starter recipe: `AgoraIO-Conversational-AI/recipe-agent-mcp` + Python `FastMCP` at `/mcp`.

**B. Custom LLM / Function Calling:**
- Custom LLM server implements OpenAI `tools` array; Agora forwards `tool_calls` and you return `tool` results inline.
- Also: `POST /agents/{id}/think` to inject instructions.

**VaayuMitra Tools (one per IMD endpoint):**
| Tool Name | IMD Endpoint | Persona |
|-----------|--------------|---------|
| `resolve_location` | Local fuzzy map `district_id` | All |
| `get_city_forecast_7d` | `/api/v1/cityforecast` | General |
| `get_city_forecast_latlon` | `/api/v1/cityforecast?lat=&lon=` | GPS fallback |
| `get_district_nowcast` | `/api/v1/districtnowcast` | Now |
| `get_rainfall_stats` | `/api/v1/districtrainfall` + `subdivision_rainfall_forecast` | Farmer |
| `get_fishermen_warning` | `/api/v1/fishermenwarning` | Fisherman |
| `get_sea_area_bulletin` | `/api/v1/seaareabulletin` + `/coastalbulleting` + `/portwarning` | Fisherman |
| `get_cyclone_track` | `/api/v1/cyclonetrack`+`cyclonewind`+`cyclonecou` | Disaster |
| `get_agromet_advisory` | Agromet bulletin API | Farmer |
| `get_all_india_warning` | `/api/v1/districtwarning` + `subdivisionwarning` | Alerts |

**IMD Auth:** Requires IP whitelisting at `https://api.imd.gov.in/public/index.php` — free, email via `api.imd.gov.in/public/api_reference.html`. Client-side caching recommended during peak events.

---

## 7. Turn Detection, Interruption & Conversation Control

**Turn Detection Structure (v2.4 revamped):**
```json
"turn_detection": {
  "mode": "default",
  "config": {
    "speech_threshold": 0.5,
    "start_of_speech": {"mode":"vad", "vad_config":{"interrupt_threshold":0.5,"prefix_padding_ms":300}},
    "end_of_speech": {"mode":"vad", "vad_config":{"silence_duration_ms":800,"pause_state_enabled":true}}
  }
}
```
- **SoS modes:** `vad`, `keywords` (Beta), `disabled` (legacy), `manual` (v2.9 — client signals via RTM)
- **EoS modes:** `vad` (silence duration), `semantic` (AI understands sentence end — EN/ZH only, falls back to vad for Indic)
- For VaayuMitra: Use `vad` for EoS + `vad` for SoS. Semantic not reliable for Indic; use `manual` only for quiz/interview mode.

**Interruption Control (v2.6 unified):**
```json
"interruption": {"enable":true,"mode":"start_of_speech"} // or keywords + keywords array
"interruption": {"enable":false,"disabled_config":{"strategy":"append"}} // queue or ignore
```
- **Legacy:** `turn_detection.interrupt_mode = adaptive/keyword` deprecated to `interruption`
- **Graceful exit:** `properties.parameters.farewell_config` — agent says goodbye before `leave` (IDLE state)
- **Greeting control:** `llm.greeting_configs = {mode:single_every/single_first, interruptable:true/false, delay_ms:0, audio_url:"https://...mp3"}` (v2.9 pre-recorded audio)

**Manual Turn Control (v2.9/2.10):**
- REST `start_of_speech.mode: manual`, `end_of_speech.mode: manual` + client toolkit `manualSOS()/manualEOS()` (Android/iOS/Web) with RTM callbacks `onUserManualSosEvent`.

**Handling via Toolkit:**
- Voice interruption: automatic on SoS detect.
- Manual interruption: `POST /agents/{id}/interrupt` or `ConversationalAIAPI.interrupt(agentId)` on client.

---

## 8. Noise Suppression & Selective Attention Locking

- **Background Noise Suppression + Echo Cancellation:** Always on, built-in. No config. Blocks background voices/interference via AI AEC/NS. Verified from product page.
- **Selective Attention Locking (SAL) Beta (v2.0):**
  ```json
  "advanced_features": {"enable_sal":true},
  "sal": {"sal_mode":1, "sample_urls":["https://.../voiceprint.wav"]}
  ```
  Register voiceprints to track primary speaker and suppress other voices/noise. Critical for fisherman boat engine + crew chatter, panchayat group calls.

**Audio Setup Best Practices:**
- `audio profile/scenario` per client (from docs `/en/ai/best-practices/audio-setup`): use `Standard / Chatroom` for voice agents.
- Data channel: `parameters.data_channel: "rtm"` required for transcripts + RTM.

---

## 9. Telephony (PSTN) & Device Kit

**Telephony Beta (v2.0 Nov 2025):**
- Outbound: `POST /v2/projects/{appid}/dial` — agent dials phone number, joins call when answered.
- Inbound: Purchase/import numbers via phone management APIs (`GET/POST /numbers`).
- Requires contacting Agora support to enable PSTN — currently free Beta, pricing TBD.
- Events: `201 inbound_call_state`, `202 outbound_call_state` webhooks.

**For VaayuMitra:** Telephony-first differentiator — farmer with feature phone dials number, same agent answers. For hackathon, apply for Beta now via Console > Talk to Us, but demo fallback via Web RTC (phone bridge simulations work for judging).

**Device Kit (R1):**
- IoT path for toys/wearables/kiosks — same conversational engine with edge chip optimization.
- Not needed for VaayuMitra web/phone, but shows scalability.

---

## 10. Pricing & Free-Tier Strategy

**Official Pricing (docs.agora.io/en/ai/reference/pricing — 2026-07-31):**

| Usage Type | Price USD/min | Free Minutes |
|---|---|---|
| Conversational AI Engine Audio Task | **0.10** (includes managed ASR/LLM/TTS) | **First 300 min free** (one-time trial, not monthly) |
| RTC Audio | 0.00099 | 10,000 min/month (shared RTC, NOT for Conv AI) |
| RTC Video HD | 0.00399 | same bucket |
| Cloud Recording Audio | 0.00149 | 10,000 min/month shared |
| Real-Time STT standalone | 0.01699/1k min | 300 min shared with translation |

**Key Notes:**
- Managed vs BYOK same $0.10/min — includes model usage when `credential_mode: managed`. Providers: ARES, Deepgram nova-2/3, OpenAI gpt-4o-mini/4.1-mini/5-nano/5-mini, MiniMax 2.6/2.8, OpenAI tts-1.
- RTC 10k free does NOT cover Conv AI — separate bucket. TRTC comparisons show Agora trial is one-time; after depletion billing starts per min.
- Billing: monthly, free quota subtracted first, then `(usage - free) * unit price` rounded to 2 decimals.
- Without purchased package: default Free package = 10k RTC mins. PCU limit 20 for server API.
- Support plans: Starter Free, Standard $449, Premium $999, Enterprise $1599.

**Free-Tier Math for Hackathon:**
- 300 Conv AI mins = ~100 demos of 3 mins.
- Budget: Dev 180 + Rehearsal 50 + Finale 5x5 = 255 min < 300.
- 10 min session = $1.0099 (0.0099+1.00) — inside free = $0.
- If no card added, service suspends after 300 — desired for hackathon.

**Stay Free Checklist:**
- Use `credential_mode: managed` where possible.
- Set `idle_timeout: 120` to avoid idle burning.
- Disable cloud recording/translation.
- Cache IMD 5 mins.
- Don't exceed 20 concurrent agents per AppID.
- Apply IP whitelisting early to avoid rate limit retries.

**Sarvam Cost if BYOK for Indic:** STT ₹30/hr, TTS ₹15-30/10k chars, Translate ₹20/10k, LLM Sarvam-M free, 30B/105B ₹29/10.9/73.2 per 1M (post 2026-08-14). Free credits ₹100-1000 never expire.

---

## 11. IMD — India Meteorological Department APIs

**Gateway:** https://api.imd.gov.in — unified gateway for forecasts, warnings, bulletins.
**Docs:** https://api.imd.gov.in/public/api_reference.html (PDF)
**Portal:** https://mausam.imd.gov.in — also https://city.imd.gov.in , https://rsmcnewdelhi.imd.gov.in (cyclone)
**Auth:** IP whitelisting via https://api.imd.gov.in/public/index.php — free, include API URL + Station ID in support tickets.

**Full Endpoint List (from docs/api_reference.html):**

*Weather Forecast APIs:*
1. City Weather Forecast (7 Days) — `GET /api/v1/cityforecast`
2. City with Lat/Lon — `.../cityforecast?lat=&lon=`
3. Subdivision Rainfall Forecast (7 Days) — `.../subdivision_rainfall_forecast`
4. State District Rainfall Forecast (5 Days) — `.../state_district_rainfall_forecast`
5. All India Weather Forecast Bulletin — `.../allindiaforecast`
6. Weather at your location (Mausamgram) — `.../mausamgram`

*Current Weather & Nowcast:*
7. Current Weather — `.../currentweather`
8. District-wise Nowcast — `.../districtnowcast`
9. Station-wise Nowcast — `.../stationnowcast`
10. AWS/ARG Data — `.../awsarg`

*Warning APIs:*
11. District-wise Warnings — `.../districtwarning?id=573`
12. Subdivision-wise Warnings — `.../subdivisionwarning`

*Rainfall APIs:*
13. District-wise Rainfall — `.../districtrainfall`
14. State-wise Rainfall — `.../staterainfall`
15. River Basin QPF — `.../riverbasinqpf`

*Marine APIs:*
16. Port Warning — `.../portwarning`
17. Sea Area Bulletin — `.../seaareabulletin`
18. Coastal Bulletin — `.../coastalbulletin`
19. Fishermen Warning — `.../fishermenwarning`

*Cyclone APIs:*
20. Cyclone Track — `.../cyclonetrack` (observed + forecast)
21. Cyclone Wind Warning — `.../cyclonewind` (GeoJSON MultiPolygon per kt)
22. Cyclone Cone of Uncertainty — `.../cyclonecou`

*Astronomical:*
23. Sun Moon Rise/Set — `.../sunmoon?lat=&lon=` (IST)

*NHAI API:* Special highway forecast.

**Sample Responses:** JSON with `status, message, totalCount, data[]`. Rainfall category codes: LE/E/N/D/LD/NR/ND. Warnings per Day_1/2/3 with color codes. Cyclone with lat/lon, MSW, kt, category.

**For VaayuMitra Mapping:** Each endpoint is a tool. Cache 5 mins. Attribution to IMD required.

---

## 12. Indic Language Stack — Sarvam AI

**Platform:** https://www.sarvam.ai — India sovereign stack, 22 languages.
**Dashboard:** https://dashboard.sarvam.ai — get API key.
**Docs:** https://docs.sarvam.ai

**Languages (TTs subset 11, STT 22):** hi-IN, bn-IN, ta-IN, te-IN, kn-IN, ml-IN, mr-IN, gu-IN, pa-IN, or-IN, en-IN, plus as-IN, ur-IN, etc.

**ASR (Saaras v2/v2.5):** 8kHz telephony + code-mixed (Hinglish) support. Param `language: hi-IN` or `unknown` auto.
```python
SarvamSTT(api_key='...', language='hi-IN')
```

**TTS (Bulbul v2/v3):** Female `anushka/manisha/vidya/arya`, Male `abhilash/karun/hitesh`. Params: `speaker, target_language_code, pitch [-0.75..0.75], pace [0.3..3.0], loudness [0.1..3.0], sample_rate [8000/16000/22050/24000]`.

**Pricing (Aug 2026):**
- Free: ₹100 (docs) — some marketing says ₹1000 — treat ₹100 floor, never expire. No card needed. 60 RPM on Starter.
- LLM Sarvam-M/30B/105B: ₹29.28 in / ₹10.98 cached / ₹73.2 out per 1M for 105B (operative rate; marketing stale).
- STT: ₹30/hr, +₹15 with diarization
- TTS: ₹15-30/10k chars
- Translate: ₹20/10k
- Plans: Pro ₹10k (+₹2k bonus), Business ₹50k (+₹12.5k bonus), Starter pay-as-you-go.

**In Agora:** Use Sarvam STT/TTS as BYOK while LLM stays managed to keep cost in free credits. Code-mixed support is differentiator for farmer Hinglish queries.

---

## 13. LLM & STT/TTS Provider Pricing

**OpenAI API (2026):**
- `gpt-4o-mini: $0.15/1M in, $0.60/1M out, cached $0.075`
- `gpt-4o: $2.50/$10`, `gpt-4.1-mini: $0.40/$1.60`, `gpt-5-nano: $0.10/$0.50`, `gpt-5-mini: $0.25/$2`, `gpt-5.5: $5/$30`
- New accounts: ~$5 free credit (3mo expiry, reports vary). Batch 50% off, prompt caching 90% off cached input.
- Whisper: $0.006/min, gpt-4o-transcribe same.

**Deepgram:**
- Free: $200 credit (~43k mins nova), never expire, no card. Post: custom plans, Growth tier for predictability. Alternative views conflict — treat $200 as current.

**Agile Free Comparison:** All-in voice agent minute with Vapi/ElevenLabs often $0.12-0.42 when adding LLM/STT/TTS + telephony. Agora's $0.10 flat simplifies.

---

## 14. Observability, Security & Limits

**Webhooks & Events:**
- `102 agent left` (reason: lifetime limit, etc)
- `103 agent history` (contents with speech_start_ms / speech_end_ms)
- `104 agent expire` (RTC token about to expire -> call `update` API)
- `110 agent error` (greeting audio failures, etc)
- `111 agent metrics` (ASR/LLM/TTS latency per turn)
- `112 turns finished` (paginated turn batches after session)
- `201/202 inbound/outbound call state` (telephony)

**Queries:**
- `GET /turns` — paginated per-turn metrics, `total_turn_count, pagination {page_index, total_pages, is_last_page}`
- `GET /history` — while running
- Client callbacks: `onTranscriptUpdated`, `onAgentListeningChanged/ThinkingChanged/SpeakingChanged`, `onMessageError`, `onAgentMetrics`

**Security:**
- RTC token generation required per channel (use SDK `expires_in_hours`).
- `rtc` encryption param for media encryption.
- `geofence` to limit server regions.
- `opt_out: true` to disable data retention.
- `labels` + `template_variables` for multi-tenant tagging (v2.1).

**Limits:**
- Max session 72 hours regardless of idle_timeout.
- 20 PCU per AppID for server API — contact support to raise.

**Troubleshooting:**
- `agora project doctor` checks credentials, feature, network.
- Check `advanced_features.enable_rtm=true` + `parameters.data_channel="rtm"` + matching channel name for transcripts.

---

## 15. Sources & Official Docs

- Product: https://www.agora.io/en/products/conversational-ai-engine/
- Docs Hub: https://docs.agora.io/en/conversational-ai/overview/product-overview
- Quickstart: https://docs.agora.io/en/ai/get-started/quickstart
- Start/Stop Agent: https://docs.agora.io/en/ai/build/start-stop-agent
- Pricing: https://docs.agora.io/en/ai/reference/pricing + https://docs.agora.io/en/conversational-ai/overview/pricing
- API Join: https://docs.agora.io/en/api-reference/api-ref/conversational-ai/join
- Release Notes: https://docs.agora.io/en/conversational-ai/overview/release-notes (v2.11 Aug 11 2026)
- Overview: https://docs.agora.io/en/introduction/conversational-ai
- Interrupt: https://docs.agora.io/en/ai/build/shape-the-conversation/interrupt-agent
- Managed Mode: https://docs.agora.io/en/ai/build/custom-model-integration/managed-mode
- Blog — Playground: https://www.agora.io/en/blog/a-playground-for-testing-voice-ai-agents/
- Blog — Voice Coder: https://www.agora.io/en/blog/build-a-voice-ai-coding-assistant-with-agora-conversational-ai/
- SDK Python: https://github.com/AgoraIO/agora-agents-python (pypi: agora-agents)
- SDK TS: https://github.com/AgoraIO/agora-agents-ts (npm: agora-agents)
- SDK Go: https://github.com/AgoraIO/agora-agents-go
- Starters: https://github.com/AgoraIO-Conversational-AI/agent-quickstart-python/nextjs/go
- Recipes: https://github.com/AgoraIO-Conversational-AI/recipe-agent-mcp, voiceprint, realtime-vendors
- IMD API Ref: https://api.imd.gov.in/public/api_reference.html
- IMD Portal: https://mausam.imd.gov.in/responsive/apis.php + https://api.imd.gov.in/public/index.php (whitelisting)
- Sarvam: https://www.sarvam.ai/api-pricing + https://docs.sarvam.ai/api/getting-started/pricing
- Pricing Comparisons: agora.io/en/pricing, trtc.io/blog, docs.agora.io/en/ai/reference/pricing
- MCP: https://mcp.agora.io
- CLI: https://github.com/AgoraIO-Community/cli

> Last verified: 2026-09-03 via webfetch/websearch. For live accuracy, re-check `docs.agora.io/llms.txt` via Agora MCP at https://mcp.agora.io

