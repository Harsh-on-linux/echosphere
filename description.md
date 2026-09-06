# VaayuMitra — Comprehensive System Architecture, Implementation & Workflow Specification

## 1. Executive Summary & Problem Statement

**VaayuMitra** is a voice-native, multilingual meteorological assistant built for rural and coastal communities across India. It bridges the critical last-mile gap between official scientific weather data—published by the **India Meteorological Department (IMD)** and the **Indian National Centre for Ocean Information Services (INCOIS)**—and ground-level citizens (farmers, fishermen, and disaster management teams).

### The Problem
- **Literacy & Digital Divide:** Traditional weather bulletins, PDFs, and mobile apps demand high literacy, smartphone proficiency, and stable data connectivity.
- **Linguistic Diversity:** India has 22 official languages and hundreds of regional dialects. Critical weather warnings are often issued in standard English or Hindi, delaying understanding in regional agrarian and coastal belts.
- **Actionable Ground Context:** Raw meteorological metrics (e.g., "35 mm rainfall, 85% RH") lack practical meaning for a farmer wondering whether to spray pesticide or harvest crops, or a fisherman deciding whether to venture 15 nautical miles out to sea.
- **Latency & Life Safety:** During cyclonic storms, extreme rainfall, or storm surges, delayed or ungrounded weather advisories directly cause loss of life and livelihood.

### The VaayuMitra Solution
VaayuMitra provides an **interruption-capable, natural voice conversation** over web browsers and standard phone lines (PSTN via Telephony). The system:
1. Resolves colloquial district and village names dynamically across Indian dialects.
2. Calls real-time IMD & INCOIS endpoints via a **FastMCP (Model Context Protocol)** tool layer.
3. Translates technical forecasts into persona-tailored, actionable advice (crop-stage specific agromet advisories, wave-height and port warnings, evacuation routes).
4. Delivers synthetic regional speech with sub-second response latency in English, Hindi, Bhojpuri, Marathi, and more.

---

## 2. End-to-End System Architecture

The following diagram illustrates the end-to-end data flow and ownership boundaries between the browser/caller, Next.js frontend, Python FastAPI backend, Agora SD-RTN, and the IMD/INCOIS data sources:

```
+-----------------------------------------------------------------------------------+
|                                 USER / CLIENT                                    |
|   Web Client (Next.js 16 / React 19)       OR       PSTN Phone Call (Telephony)   |
+--------------------------+----------------------------------------+---------------+
                           |                                        |
                 Audio / Video (WebRTC)                             | SIP / E.164
                           |                                        |
+--------------------------v----------------------------------------v---------------+
|                      AGORA SOFTWARE-DEFINED REAL-TIME NETWORK (SD-RTN)             |
|                                                                                   |
|   +---------------------------------------------------------------------------+   |
|   |                     Agora Conversational AI Engine                        |   |
|   |                                                                           |   |
|   |  +--------------------+    +--------------------+    +-----------------+  |   |
|   |  |   ASR / STT Stage  |    |     LLM Stage      |    |    TTS Stage    |  |   |
|   |  | Deepgram / Sarvam  |--->|   OpenAI 4o-mini   |--->| MiniMax/Sarvam  |  |   |
|   |  +--------------------+    +---------+----------+    +-----------------+  |   |
|   +--------------------------------------|------------------------------------+   |
+------------------------------------------|----------------------------------------+
                                           | Tool Call (Streamable HTTP JSON-RPC)
                                           | POST /mcp
                                           v
+-----------------------------------------------------------------------------------+
|                           VAAYUMITRA BACKEND (FastAPI)                             |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  | FastMCP Tool Server (/mcp)                                                  |  |
|  |  - get_district_forecast      - get_cyclone_warnings   - get_crop_advisory  |  |
|  |  - get_district_nowcast       - get_marine_bulletin    - emergency_sos      |  |
|  +---------------------------------------+-------------------------------------+  |
|                                          |                                        |
|  +---------------------------------------v-------------------------------------+  |
|  | Location Resolver & Spatial Engine                                          |  |
|  |  - RapidFuzz Matcher (700+ Districts)  - LGD Code Mapper  - Haversine Fallback|  |
|  +---------------------------------------+-------------------------------------+  |
|                                          |                                        |
|  +---------------------------------------v-------------------------------------+  |
|  | IMD / INCOIS Client with Circuit Breaker & TTL 300s Cache                  |  |
|  +-----------------------------------------------------------------------------+  |
+------------------------------------------+----------------------------------------+
                                           | HTTPS REST Requests
                                           v
+-----------------------------------------------------------------------------------+
|                           EXTERNAL DATA SOURCES                                    |
|   - IMD Mausam APIs (Rainfall, Nowcast, Agro Advisory, Radar/Satellite)           |
|   - INCOIS Ocean State Forecasts (Wave Height, Swell Surge, PFZ)                  |
|   - Cyclone eAtlas Archives & Open-Meteo Fallbacks                                |
+-----------------------------------------------------------------------------------+
```

---

## 3. Technology Stack Breakdown

| Subsystem | Technology | Purpose / Configuration |
|---|---|---|
| **Voice & Real-Time** | Agora SD-RTN | Ultra-low latency audio delivery (<200ms glass-to-glass) |
| | Agora Conversational AI Engine | Cloud orchestration of STT -> LLM -> TTS pipelines |
| | Agora RTC SDK (`agora-rtc-sdk-ng` 4.24) | Client-side media stream transmission |
| | Agora RTM SDK (`agora-rtm` 2.2) | Low-latency transcript and agent state messaging |
| | Agora Agent Server SDK (`agora-agents` 2.7) | Python server lifecycle orchestration |
| **Backend Core** | Python 3.11 + FastAPI 0.141 | REST APIs, token generation, agent lifecycle |
| | FastMCP 4.0 | Stateless Streamable HTTP JSON-RPC tool server |
| | RapidFuzz 3.14 | Sub-millisecond phonetic and fuzzy district matching |
| | Cachetools & Tenacity | 300s TTL cache with retry logic and offline mock fallback |
| | Uvicorn 0.52 | ASGI production server |
| **Frontend UI** | Next.js 16 (App Router, Turbopack) | Server-side rendering, client hydration, API rewrites |
| | React 19 | Declarative UI state management |
| | Agora Agent UIKit 1.1 | VoiceOrb visualizer, waveform, and audio controls |
| | Tailwind CSS & Radix UI | Modern responsive interface, modals, accessibility |
| | Leaflet 1.9 & React-Leaflet | Cyclone eAtlas GeoJSON tracking and radar overlays |
| **Speech & LLM** | Deepgram Nova-2 / Nova-3 | High-accuracy English and multilingual STT |
| | Sarvam AI Saarika v2 | Specialized Indic speech recognition (Devanagari) |
| | OpenAI GPT-4o-mini | Conversational reasoning, persona shaping, tool invocation |
| | MiniMax Speech-02 | Natural low-latency English TTS |
| | Sarvam AI Bulbul v3 | Expressive Indic TTS (`anushka`, `priya`, `aditya`) |

---

## 4. End-to-End Workflow & Lifecycle

The lifecycle of a VaayuMitra interaction consists of five synchronized phases:

### Phase 1: Connection & Authentication (Token007)
1. The user clicks **"Start conversation"** or triggers an incoming phone call.
2. The frontend sends a `GET /api/get_config` request.
3. Next.js proxies this request to FastAPI `/get_config`.
4. The backend uses `agora_agent.agentkit.token.generate_convo_ai_token`:
   - Builds a single unified **Token007 (AccessToken2)** valid for both RTC (audio) and RTM (signaling).
   - Generates unique randomized `uid`, `channel_name`, and assigns `agent_uid`.
   - Returns connection credentials to the frontend.
5. The frontend initializes `AgoraRTC` and `AgoraRTM` clients, joins the channel, and subscribes to signaling.

### Phase 2: Agent Session Initialization
1. Once RTC and RTM connection is established, the client calls `POST /api/startAgent` passing:
   - `channelName`: The unique RTC channel.
   - `userUid`: Client user ID.
   - `language`: Target language (e.g., `hi-IN`, `mr-IN`, `bho-IN`, `en-US`).
   - `persona`: Persona context (`farmer`, `fisherman`, `disaster`).
   - `lat`/`lon`: Optional GPS geolocation from the browser.
2. FastAPI dynamically constructs the `Agent` session:
   - **Indic Pipeline:** If Indic language is requested, configures Sarvam STT (`saarika:v2`) and Sarvam TTS (`bulbul:v3`).
   - **Global Pipeline:** Otherwise, configures Deepgram STT (`nova-2`) and MiniMax TTS (`speech-2.6-turbo`).
   - **LLM Configuration:** Mounts OpenAI `gpt-4o-mini`, injects persona system prompts, and registers `llm.mcp_servers` pointing to the `/mcp` tool server.
3. The backend starts the agent session via the Agora Conversational AI REST API and returns `agent_id`.

### Phase 3: Conversational Voice Loop & FastMCP Tool Execution
1. The user speaks into their microphone:
   - Audio is streamed over Agora SD-RTN to the Conversational AI Engine.
   - STT transcribes speech into text in real-time.
   - Voice Activity Detection (VAD) detects speech boundaries and handles conversational interruptions instantly.
2. When the user asks a meteorological question (e.g., *"Will it rain in Nashik tomorrow, and can I spray my onions?"*):
   - The LLM detects the need for real-world weather data.
   - The LLM issues a tool call over FastMCP: `POST /mcp` with method `tools/call` and parameters `{"district": "Nashik", "crop": "onion"}`.
   - The FastMCP server resolves "Nashik" via `location_resolver.py` to district ID `492`.
   - `imd_client.py` fetches the 5-day forecast and agromet advisory.
   - The tool returns structured JSON with an IMD official source timestamp.
3. The LLM synthesizes a concise, persona-grounded response citing official IMD data.
4. The TTS engine streams the generated audio back into the RTC channel while simultaneously broadcasting transcript events over RTM.

### Phase 4: Teardown & Session Snapshotting
1. When the user clicks **"End Conversation"** or 120 seconds of silence elapse (`idle_timeout`):
   - `POST /api/stopAgent` is triggered to release Agora AI Engine cloud resources.
   - Pre-session history (`/agentHistory`) and turns (`/agentTurns`) are retrieved and saved to client-side `localStorage` for post-session analytics.
   - RTC tracks are closed and RTM unbinds.

---

## 5. Core Subsystems & Implementation Details

### 5.1 FastMCP Tool Server (`server/src/mcp_server.py`)
Mounted directly at FastAPI route `/mcp` using stateless streamable HTTP JSON-RPC:
- **`get_district_forecast(district, state)`**: 5-day daily forecast (rainfall probability, temp min/max, wind speed, humidity).
- **`get_district_nowcast(district)`**: 3-hour localized convective storm, lightning, and squall alerts.
- **`get_cyclone_warnings(region)`**: Active cyclonic depression tracks, landfall estimates, and cone-of-uncertainty coordinates.
- **`get_marine_bulletin(coastal_zone)`**: Wave heights, swell alerts, wind gusts, and INCOIS safe-navigation boundaries for fishermen.
- **`get_crop_weather_advisory(district, crop, growth_stage)`**: Agromet bulletins indicating spraying conditions, irrigation needs, and moisture stress.
- **`get_radar_image_meta(radar_station)`**: Doppler Weather Radar (DWR) composite reflectivity status and precipitation intensity.
- **`get_satellite_cloud_meta(sector)`**: INSAT-3D thermal infrared and visible cloud-top brightness temperatures.
- **`resolve_location(query)`**: High-speed fuzzy search returning canonical district name, state, and coastal status.
- **`emergency_sos_broadcast(district, severity, message)`**: Dispatches critical disaster advisories and returns emergency helpline coordinates.

### 5.2 Location Resolver & Spatial Engine (`server/src/location_resolver.py`)
- Pre-indexes 700+ Indian districts from `data/imd_districts.json`.
- Uses RapidFuzz token set matching with alias substitution (e.g., "Baroda" -> "Vadodara", "Banaras" -> "Varanasi", "Bombay" -> "Mumbai").
- Supports multilingual phonetic transliteration (e.g., Devanagari "नासिक" -> "Nashik").
- Implements Haversine distance spatial lookup: if a GPS coordinate is provided or a village is not found, resolves the nearest three meteorological stations.

### 5.3 Multi-Persona System (`server/src/persona_prompt.py`)
- **Farmer Persona (`farmer`):**
  - Focuses on precipitation windows, soil saturation, humidity thresholds for fungal disease, and optimal spraying temperatures.
  - Conversational style: Respectful, practical, agrarian terminology.
- **Fisherman Persona (`fisherman`):**
  - Focuses on sea conditions, wind knots, wave heights, distance from shore, and INCOIS Potential Fishing Zones (PFZ).
  - Explicit safety guard: Warns emphatically when wind speeds exceed 45 km/h or high wave alerts are active.
- **Disaster Management Persona (`disaster`):**
  - Focuses on emergency alerts, flash flood risks, cyclone cones, evacuation protocols, and emergency helpline numbers (1077/112).
  - Conversational style: Urgent, clear, directive, avoiding ambiguous language.

### 5.4 Multilingual Voice Matrix
VaayuMitra supports both global managed voice pipelines and native Indic voice models:
- **English (Global):** Deepgram Nova-2 STT -> GPT-4o-mini -> MiniMax `speech-2.6-turbo`.
- **Hindi (`hi-IN`):** Sarvam Saarika v2 STT -> GPT-4o-mini -> Sarvam Bulbul v3 (`anushka` or `aditya`).
- **Bhojpuri (`bho-IN`):** Specialized Devanagari phonetic prompt tuning via Sarvam Saarika + Bulbul.
- **Marathi (`mr-IN`):** Dialect-adapted Marathi pipeline with Turn Detection mapped safely to compatible VAD standards.

### 5.5 Interactive Cyclone eAtlas & Radar Map (`web/src/components/CycloneMapModal.tsx`)
- Integrated Leaflet map displaying live cyclonic disturbances in the North Indian Ocean (Bay of Bengal and Arabian Sea).
- GeoJSON rendering of cyclone tracks: past points, present eye position, and 48-hour projected cone of uncertainty with wind radii.
- Color-coded intensity categories according to IMD standards:
  - Depression (D): 31–49 km/h (Blue)
  - Deep Depression (DD): 50–61 km/h (Cyan)
  - Cyclonic Storm (CS): 62–88 km/h (Yellow)
  - Severe Cyclonic Storm (SCS): 89–117 km/h (Orange)
  - Very Severe Cyclonic Storm (VSCS): 118–165 km/h (Red)
  - Extremely Severe Cyclonic Storm (ESCS): 166–221 km/h (Purple)
  - Super Cyclonic Storm (SuCS): ≥222 km/h (Magenta)

### 5.6 Telephony Beta & Landline Access (`server/src/telephony.py`)
- Outbound dialing via Agora Telephony Beta (`POST /dial`) enabling voice calls to standard feature phones (E.164 formatting, e.g., `+919876543210`).
- Webhook endpoints (`POST /telephonyWebhook`) handling incoming PSTN calls.
- Simulated phone bridge fallback for live testing without SIP trunk credentials.

---

## 6. API Reference Catalog

### Frontend-to-Backend Rewrites (`web/next.config.ts`)
Next.js proxies all `/api/*` routes directly to the FastAPI service at `http://localhost:8000`:

| Endpoint | Method | Request Payload | Response / Purpose |
|---|---|---|---|
| `/get_config` | GET | `?query=...` | Returns Token007, `channel_name`, `uid`, `agent_uid` |
| `/startAgent` | POST | `{ channelName, rtcUid, userUid, language, persona, lat, lon, voice }` | Starts Agora AI Agent session, returns `agent_id` |
| `/stopAgent` | POST | `{ agentId }` | Terminates active agent cloud session |
| `/interruptAgent`| POST | `{ agentId }` | Interrupts current agent speech immediately |
| `/agentHistory` | GET | `?agentId=...` | Retrieves conversation transcript history |
| `/agentTurns` | GET | `?agentId=...&pageSize=50` | Retrieves granular turn-by-turn latency metrics |
| `/cycloneMap` | GET | — | Returns GeoJSON FeatureCollection of active cyclone tracks |
| `/dial` | POST | `{ toNumber }` | Initiates PSTN outbound phone call via Telephony Beta |
| `/hangup` | POST | `{ agentId }` | Terminates active PSTN phone call |
| `/telephonyStatus` | GET | — | Returns status of Telephony Beta configuration |
| `/health` | GET | — | Diagnostic report (Agora credentials, IMD cache, MCP URL) |
| `/mcp` | POST | JSON-RPC 2.0 | FastMCP tool invocation protocol |

---

## 7. Cost, Resource & Free-Tier Guardrails

To ensure production stability while remaining strictly within hackathon free tiers:
1. **Managed Credential Mode:** Uses Agora-managed accounts for Deepgram, OpenAI, and MiniMax, avoiding personal API key rate limits and billing surcharges.
2. **Idle Timeout Guard (`idle_timeout: 120`):** Automatically terminates the cloud voice session after 2 minutes of conversational inactivity, preventing accidental minute burn.
3. **Tab Teardown Listener:** Automatically sends `stopAgent` on browser window unload (`beforeunload`).
4. **IMD Cache TTL (300s):** Caches all external weather API responses for 5 minutes in memory, shielding government servers from high-frequency queries.
5. **Circuit Breaker & Mock Fallback:** Automatically serves realistic offline sample data if IMD endpoints experience downtime or latency spikes >5s.
6. **No Cloud Recording:** Cloud recording and storage services are explicitly disabled to prevent storage billing.

---

## 8. Directory & File Organization

```
echosphere/
├── README.md                     # Project overview and run guides
├── ARCHITECTURE.md               # High-level architecture summary
├── description.md                # Comprehensive system & implementation specification (this file)
├── plan.md                       # Phased development roadmap
├── research.md                   # IMD, INCOIS, and Agora API reference notes
├── AGENTS.md                     # AI agent operational rules and commit standards
├── package.json                  # Root workspace script definitions
├── data/
│   ├── imd_districts.json        # 700+ Indian districts with coordinates and coastal metadata
│   └── sample_imd_responses/     # Offline mock responses for resilient fallback
├── scripts/
│   ├── start-backend.ts          # Cross-platform Python venv detection and backend launcher
│   ├── start-frontend.ts         # Cross-platform Next.js frontend launcher
│   ├── setup-env.ts              # Zero-dependency environment file preparer
│   └── verify-deploy.sh          # Deployment validation script
├── server/                       # Python FastAPI Backend
│   ├── requirements.txt          # Production dependencies
│   ├── requirements-dev.txt      # Testing and linting tools
│   ├── src/
│   │   ├── server.py             # FastAPI entrypoint, routes, and middleware
│   │   ├── agent.py              # Agora Conversational AI Agent builder and pipeline logic
│   │   ├── mcp_server.py         # FastMCP meteorological tools server
│   │   ├── imd_client.py         # IMD API client with TTL caching and circuit breaker
│   │   ├── location_resolver.py  # RapidFuzz district search and LGD code resolver
│   │   ├── persona_prompt.py     # System prompt templates per user persona
│   │   ├── spatial_reasoning.py  # Geographic distance calculations and coastal checks
│   │   ├── bulletin_cache.py     # Regional bulletin caching engine
│   │   ├── telephony.py          # Telephony Beta SIP / PSTN bridge
│   │   ├── user_store.py         # In-memory user profile management
│   │   └── whatsapp_service.py   # WhatsApp summary dispatcher
│   └── tests/                    # Comprehensive pytest test suite (205 tests)
└── web/                          # Next.js 16 Frontend
    ├── package.json              # Web dependencies
    ├── next.config.ts            # Route rewrites and Webpack/Turbopack settings
    └── src/
        ├── app/                  # Next.js App Router root layout and page
        ├── components/
        │   ├── LandingPage.tsx   # Top-level orchestrator and RTC/RTM manager
        │   ├── ConversationComponent.tsx  # Active voice UI and live visualizer
        │   ├── VoiceSettingsPanel.tsx     # Persona, language, and voice selector
        │   ├── CycloneMapModal.tsx        # Leaflet cyclone and radar map
        │   ├── PhoneCallModal.tsx         # Telephony dial pad interface
        │   ├── SessionHistoryPanel.tsx    # Post-conversation analytics and snapshot list
        │   └── AgentMetricsOverlay.tsx    # Live pipeline latency monitor
        ├── lib/
        │   ├── conversation.ts   # Transcript normalization and latency helpers
        │   └── sessionHistory.ts # LocalStorage session persistence and deduplication
        └── services/
            └── api.ts            # Typed client for backend API communication
```

---

## 9. Verification & Quality Assurance

- **Unit & Integration Tests:**
  - Backend: 205 passing unit tests (`pytest server/tests`).
  - Frontend: 23 passing TypeScript tests (`bun test` in `web/`).
- **Syntax & Type Checking:**
  - Python: Clean compilation (`python -m py_compile server/src/*.py`).
  - TypeScript: Full Next.js production build passes with Turbopack and zero type errors (`bun run build`).
- **Real-Time Latency Verification:**
  - Glass-to-glass conversational latency consistently measured below 1.2s across 4G and broadband connections.
