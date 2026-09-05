"""
Agent

High-level API for managing Agora Conversational AI Agents.
"""
import logging
import os
import random
import re
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from pydantic import ConfigDict
from agora_agent import Area, AsyncAgora
from agora_agent.agentkit import Agent as AgoraAgent, SalConfig
from agora_agent.agentkit.token import generate_convo_ai_token
from agora_agent.agentkit.vendors import (
    DeepgramSTT,
    MiniMaxTTS,
    OpenAI,
    SarvamSTT,
)
from agora_agent.agentkit.vendors.tts import BaseTTS


class SarvamV3TTS(BaseTTS):
    """Sarvam AI bulbul:v3 text-to-speech vendor adapter for Agora Conversational AI."""
    model_config = ConfigDict(extra="allow")

    key: str
    speaker: str = "priya"
    target_language_code: str = "hi-IN"
    model: str = "bulbul:v3"
    pace: Optional[float] = None
    pitch: Optional[float] = None
    loudness: Optional[float] = None
    sample_rate: Optional[int] = None
    skip_patterns: Optional[list] = None

    def to_config(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "api_subscription_key": self.key,
            "speaker": self.speaker,
            "target_language_code": self.target_language_code,
            "model": self.model,
        }
        if self.pace is not None:
            params["pace"] = self.pace
        if self.pitch is not None:
            params["pitch"] = self.pitch
        if self.loudness is not None:
            params["loudness"] = self.loudness
        if self.sample_rate is not None:
            params["sample_rate"] = self.sample_rate

        result: Dict[str, Any] = {"vendor": "sarvam", "params": params}
        if self.skip_patterns is not None:
            result["skip_patterns"] = self.skip_patterns
        return result

try:
    from persona_prompt import (
        DEFAULT_PERSONA,
        FILLER_WORDS,
        GREETINGS,
        GREETING_CONFIGS,
        INDIC_LANGUAGES,
        PERSONA_TTS_RATE,
        SARVAM_SPEAKER,
        TURN_DETECTION_LANGUAGE,
        WEATHERGPT_SYSTEM,
        get_greeting,
        get_system_prompt,
        normalize_language,
        normalize_persona,
    )
except ImportError:  # pragma: no cover - fallback when run from a different cwd
    from src.persona_prompt import (  # type: ignore
        DEFAULT_PERSONA,
        FILLER_WORDS,
        GREETINGS,
        GREETING_CONFIGS,
        INDIC_LANGUAGES,
        PERSONA_TTS_RATE,
        SARVAM_SPEAKER,
        TURN_DETECTION_LANGUAGE,
        WEATHERGPT_SYSTEM,
        get_greeting,
        get_system_prompt,
        normalize_language,
        normalize_persona,
    )

logger = logging.getLogger("uvicorn.error")

# Phase 2.1 — WeatherGPT managed voice loop (plan.md 2.1, research.md #5).
# Agora is central: ASR->LLM->TTS runs in the Conversational AI Engine.
# Free-tier first: managed Deepgram + gpt-4o-mini + MiniMax (no BYOK keys).
WEATHERGPT_GREETING = GREETINGS["en-IN"]
WEATHERGPT_FAILURE = (
    "IMD data is busy right now. Last update was a few minutes ago. "
    "Please try again in a moment."
)
WEATHERGPT_MAX_HISTORY = 10
# Free-tier guard: auto-leave after 2 min silence (plan.md 2.1/2.3, AGENTS.md #5).
WEATHERGPT_IDLE_TIMEOUT = 120


# Phase 6.3 — Telephony (PSTN) via Agora Telephony Beta (research.md #9).
# Outbound dial uses AsyncAgora.telephony.call (SIP); inbound 201/202
# call-state events land on POST /telephonyWebhook (server.py). Until Agora
# grants Beta access, TELEPHONY_ENABLED stays false and /dial answers 501
# with setup steps — the phone-bridge fallback (mobile on speaker near the
# laptop mic) proves the same voice loop with zero PSTN cost.
class TelephonyDisabledError(RuntimeError):
    """PSTN dialed before the Telephony Beta is enabled (maps to HTTP 501)."""


TELEPHONY_SETUP_GUIDE = (
    "Telephony Beta is not enabled. Steps: 1) Agora Console > Talk to Us > "
    "request Telephony Beta (mention SIH26068). 2) Set TELEPHONY_ENABLED=true "
    "and TELEPHONY_FROM_NUMBER=+<your-agora-number> with CUSTOMER_ID/SECRET. "
    "3) Redeploy and point the Console webhook at POST /telephonyWebhook. "
    "Meanwhile use the phone-bridge fallback: call the demo laptop from any "
    "phone on speaker next to its mic."
)

_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def parse_e164_number(raw: Any, field: str = "phone number") -> str:
    """Normalize to E.164, raising ValueError (HTTP 400) for bad input.

    The leading + (country code) is mandatory — never guess it, or
    9876543210 could dial the wrong country.
    """
    text = re.sub(r"[\s\-().]", "", str(raw or ""))
    if not _E164_RE.match(text):
        raise ValueError(f"invalid {field}: {raw!r} — expected E.164 like +919876543210")
    return text


def telephony_status_info() -> Dict[str, Any]:
    """PSTN readiness from env only (no Agora cloud call)."""
    enabled_flag = (os.getenv("TELEPHONY_ENABLED") or "").strip().lower() in {"1", "true", "yes", "on"}
    from_number = (os.getenv("TELEPHONY_FROM_NUMBER") or "").strip()
    customer_auth = bool((os.getenv("CUSTOMER_ID") or "").strip() and (os.getenv("CUSTOMER_SECRET") or "").strip())
    enabled = enabled_flag and bool(from_number) and customer_auth
    return {
        "enabled": enabled,
        "mode": "beta-direct" if enabled else "phone-bridge-fallback",
        "from_number_configured": bool(from_number),
        "customer_auth_configured": customer_auth,
        "webhook_path": "/telephonyWebhook",
    }


def get_sal_config() -> Optional[Dict[str, Any]]:
    """Return opt-in SAL settings when a public voiceprint is configured.

    Agora's built-in noise suppression remains enabled for every audio session.
    SAL is an extra voiceprint feature, so keep it disabled unless explicitly
    enabled and fail closed when the sample URL is missing or unsafe.
    """
    enabled = (os.getenv("SAL_ENABLED") or "").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return None

    sample_url = (os.getenv("SAL_SAMPLE_URL") or "").strip()
    parsed = urlparse(sample_url)
    if parsed.scheme != "https" or not parsed.netloc:
        logger.warning("SAL_ENABLED is true but SAL_SAMPLE_URL is not a valid HTTPS URL; SAL disabled")
        return None

    mode = (os.getenv("SAL_MODE") or "locking").strip().lower()
    if mode not in {"locking", "recognition"}:
        logger.warning("Unsupported SAL_MODE=%s; expected locking or recognition; SAL disabled", mode)
        return None

    return {"sal_mode": mode, "sample_urls": {"default": sample_url}}


def get_mcp_servers() -> Optional[list]:
    """Build llm.mcp_servers for Agora (plan.md 3.3, research.md #6).

    Agora cloud POSTs {endpoint} (JSON-RPC, streamable_http) when the LLM
    decides to use an IMD tool. Endpoint must be public HTTPS in prod
    (plan.md 6.1); localhost only verifies config shape in tests. Returns
    None when unconfigured so managed-only sessions stay voice-only.
    """
    explicit = (os.getenv("MCP_SERVER_URL") or os.getenv("MCP_ENDPOINT") or "").strip()
    if explicit:
        url = explicit
    else:
        backend = (os.getenv("BACKEND_URL") or "").strip().rstrip("/")
        if not backend:
            logger.warning(
                "MCP URL unconfigured (set MCP_SERVER_URL or BACKEND_URL); "
                "starting voice-only without IMD tools"
            )
            return None
        url = f"{backend}/mcp"
    if not url.startswith("https://") and "localhost" not in url and "127.0.0.1" not in url:
        logger.warning("MCP endpoint %s is not public HTTPS; Agora cloud tool calls will fail", url)
    # NOTE: Agora REST field is "endpoint", not "url" (see join API +
    # recipe-agent-mcp mcp_config.py). Wrong key is silently ignored.
    return [{"name": "imd", "endpoint": url, "transport": "streamable_http"}]


class Agent:
    """
    High-level wrapper for Agora Conversational AI Agent operations.
    
    Uses AgentSession for full lifecycle management (start/stop),
    which handles Token007 authentication automatically.
    """
    
    def __init__(self):
        self.app_id = os.getenv("AGORA_APP_ID")
        self.app_certificate = os.getenv("AGORA_APP_CERTIFICATE")
        self.greeting = WEATHERGPT_GREETING
        self.failure_message = WEATHERGPT_FAILURE

        if not self.app_id or not self.app_certificate:
            raise ValueError("AGORA_APP_ID and AGORA_APP_CERTIFICATE are required")

        # Phase 6.3: REST (Basic) auth for telephony/phone-numbers APIs.
        # Optional — voice sessions work without it; /dial needs it.
        client_kwargs: Dict[str, Any] = {}
        customer_id = (os.getenv("CUSTOMER_ID") or "").strip()
        customer_secret = (os.getenv("CUSTOMER_SECRET") or "").strip()
        if customer_id and customer_secret:
            client_kwargs["customer_id"] = customer_id
            client_kwargs["customer_secret"] = customer_secret
        self.client = AsyncAgora(
            area=Area.US,
            app_id=self.app_id,
            app_certificate=self.app_certificate,
            **client_kwargs,
        )

        # Track active sessions by agent_id
        self._sessions: Dict[str, Any] = {}
        # Agent IDs created via PSTN dial (hangup path, not RTC stop)
        self._telephony_ids: set = set()

    async def start(
        self,
        channel_name: str,
        agent_uid: int,
        user_uid: int,
        output_audio_codec: Optional[str] = None,
        language: Optional[str] = None,
        persona: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        phone_number: Optional[str] = None,
        voice: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start agent with the same default vendor chain as the Next.js quickstart."""
        if not channel_name or not str(channel_name).strip():
            raise ValueError("channel_name is required and cannot be empty")
        if agent_uid <= 0:
            raise ValueError("agent_uid is required and cannot be empty")
        if user_uid <= 0:
            raise ValueError("user_uid is required and cannot be empty")

        # Phase 4.1 — Indic pipeline (plan.md 4.1, research.md #12).
        # en-IN (or missing Sarvam key): managed Deepgram + MiniMax, inside the
        # $0.10/min bundle and 300 free mins. hi/ta/mr/bn-IN with SARVAM_API_KEY:
        # Sarvam BYOK (₹100 free, code-mixed Hinglish support). "auto" uses
        # Sarvam `unknown` STT auto-detect. Selecting Sarvam voice activates
        # Sarvam STT+TTS even in Indian English (en-IN).
        voice_language = normalize_language(language)
        sarvam_key = (os.getenv("SARVAM_API_KEY") or "").strip()
        voice_lower = (voice or "").strip().lower()
        use_sarvam = bool(sarvam_key) and (
            voice_language in INDIC_LANGUAGES
            or voice_language == "auto"
            or "sarvam" in voice_lower
            or "anushka" in voice_lower
        )
        greeting = get_greeting(voice_language)
        turn_language = TURN_DETECTION_LANGUAGE.get(voice_language, "en-US")
        try:
            from agora_agent.agentkit.agent import _is_turn_detection_language
            if not _is_turn_detection_language(turn_language):
                turn_language = "hi-IN" if voice_language in INDIC_LANGUAGES else "en-US"
        except Exception:
            pass
        # Phase 4.2 — persona hint selects the system prompt + TTS rate.
        voice_persona = normalize_persona(persona)
        instructions = get_system_prompt(voice_persona)
        tts_rate = PERSONA_TTS_RATE.get(voice_persona, 1.0)

        # Phase 1.3: Geolocation handshake — inject GPS coordinates and nearest region into instructions
        if lat is not None and lon is not None:
            try:
                from location_resolver import find_nearest_location
                nearest = find_nearest_location(lat, lon)
                if nearest:
                    place = nearest.get("tehsil") or nearest["district_name"]
                    instructions += (
                        f"\nUser GPS coordinates: ({lat:.4f}, {lon:.4f}), nearest region: {place}, {nearest['state']}. "
                        f"Assume this location by default unless the user specifies otherwise."
                    )
            except Exception:
                pass

        # Phase 5: Caller profile & persistent farm memory handshake
        if phone_number:
            try:
                from user_store import get_profile_context
                p_ctx = get_profile_context(phone_number)
                if p_ctx:
                    instructions += f"\nCaller Profile: {p_ctx}"
            except Exception:
                pass

        # Default managed path: DeepgramSTT + OpenAI + MiniMaxTTS (plan.md 2.1).
        # Managed = included in the $0.10/min Conv AI price, inside 300 free mins.
        # Phase 3.3: attach IMD MCP so the LLM can call resolve_location +
        # forecast/warning tools via POST {BACKEND_URL}/mcp (enable_tools below).
        mcp_servers = get_mcp_servers()
        llm_kwargs: Dict[str, Any] = dict(
            model="gpt-4o-mini",
            system_messages=[{"role": "system", "content": instructions}],
            greeting_message=greeting,
            failure_message=self.failure_message,
            max_history=WEATHERGPT_MAX_HISTORY,
            max_tokens=1024,
            temperature=0.7,
            top_p=0.95,
        )
        if mcp_servers is not None:
            llm_kwargs["mcp_servers"] = mcp_servers
        llm = OpenAI(**llm_kwargs)
        if use_sarvam:
            stt_language = "unknown" if voice_language == "auto" else voice_language
            tts_language = "en-IN" if voice_language in ("auto", "en", "en-IN") else voice_language
            speaker = SARVAM_SPEAKER
            if voice:
                v_clean = voice.strip().lower()
                if v_clean in ("anushka", "anushka_v2", "priya"):
                    speaker = "priya"
                elif v_clean in ("aditya", "rahul", "ashutosh", "rohan", "amit", "ritu", "neha", "pooja", "simran", "kavya"):
                    speaker = v_clean
                else:
                    speaker = "priya"
            stt = SarvamSTT(api_key=sarvam_key, language=stt_language)
            tts = SarvamV3TTS(
                key=sarvam_key,
                speaker=speaker,
                target_language_code=tts_language,
                model="bulbul:v3",
                pace=tts_rate,
            )
            stt_name, tts_name = "sarvam", "sarvam"
        else:
            stt = DeepgramSTT(model="nova-3", language="en")
            tts = MiniMaxTTS(model="speech_2_6_turbo", voice_id="English_captivating_female1",
                             speed=tts_rate)
            stt_name, tts_name = "deepgram", "minimax"

        logger.info(
            "Selected voice pipeline stt=%s tts=%s voice_language=%s voice=%s use_sarvam=%s",
            stt_name,
            tts_name,
            voice_language,
            voice,
            use_sarvam,
        )

        # Optional BYOK example: replace the STT block above and set DEEPGRAM_API_KEY.
        # stt = DeepgramSTT(api_key=os.getenv("DEEPGRAM_API_KEY"), model="nova-3", language="en")

        # Optional BYOK example: replace the LLM block above and set OPENAI_API_KEY.
        # llm = OpenAI(
        #     api_key=os.getenv("OPENAI_API_KEY"),
        #     model="gpt-4o-mini",
        #     greeting_message="Hello! I am your AI assistant. How can I help you?",
        #     failure_message="I'm sorry, I'm having trouble processing your request.",
        #     max_history=15,
        #     max_tokens=1024,
        #     temperature=0.7,
        #     top_p=0.95,
        # )

        # Optional BYOK example: replace the TTS block above and set ELEVENLABS_API_KEY.
        # from agora_agent.agentkit.vendors import ElevenLabsTTS
        # tts = ElevenLabsTTS(
        #     key=os.getenv("ELEVENLABS_API_KEY"),
        #     model_id="eleven_flash_v2_5",
        #     voice_id=os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB"),
        # )

        parameters = {
            # Agora's audio scenario includes built-in noise suppression and
            # echo cancellation; SAL below is an optional extra layer.
            "audio_scenario": "chorus",  # web client -> ultra-low-latency profile
            "data_channel": "rtm",
            "enable_error_message": True,
            "enable_metrics": True,
        }
        if isinstance(output_audio_codec, str) and output_audio_codec.strip():
            parameters["output_audio_codec"] = output_audio_codec.strip()

        sal_config = get_sal_config()
        advanced_features = {"enable_rtm": True, "enable_tools": True}
        if sal_config is not None:
            advanced_features["enable_sal"] = True

        agora_agent = AgoraAgent(
            client=self.client,
            instructions=instructions,
            greeting=greeting,
            failure_message=self.failure_message,
            max_history=WEATHERGPT_MAX_HISTORY,
            # Phase 4.3: single interruptable greeting + static fillers mask
            # IMD tool-call latency ("Ek second, IMD check kar raha hun...").
            greeting_configs=dict(GREETING_CONFIGS),
            filler_words=dict(FILLER_WORDS),
            turn_detection={
                "language": turn_language,
                "mode": "default",
                "config": {
                    "speech_threshold": 0.5,
                    "start_of_speech": {
                        "mode": "vad",
                        "vad_config": {
                            # Balanced for quiet rooms and short spoken
                            # interruptions such as "Ruko" or "Nahi".
                            "interrupt_threshold": 0.5,
                            "prefix_padding_ms": 250,
                        },
                    },
                    "end_of_speech": {
                        "mode": "vad",
                        "vad_config": {
                            "silence_duration_ms": 700,
                            "pause_state_enabled": True,
                        },
                    },
                },
            },
            interruption={"enable": True, "mode": "start_of_speech"},
            sal=SalConfig(**sal_config) if sal_config is not None else None,
            advanced_features=advanced_features,
            parameters=parameters,
        )
        
        agora_agent = (
            agora_agent
            .with_stt(stt)
            .with_llm(llm)
            .with_tts(tts)
        )

        session = agora_agent.create_async_session(
            channel=channel_name,
            agent_uid=str(agent_uid),
            remote_uids=[str(user_uid)],
            enable_string_uid=False,
            idle_timeout=WEATHERGPT_IDLE_TIMEOUT,
            expires_in=3600,
            name=f"wx-{int(time.time())}",
        )

        logger.info(
            "Starting Agora agent channel=%s agent_uid=%s user_uid=%s",
            channel_name,
            agent_uid,
            user_uid,
        )

        try:
            agent_id = await session.start()
        except Exception:
            logger.exception(
                "Failed to start Agora agent channel=%s agent_uid=%s user_uid=%s",
                channel_name,
                agent_uid,
                user_uid,
            )
            raise

        # Save session for later stop
        self._sessions[agent_id] = session

        logger.info(
            "Started Agora agent agent_id=%s channel=%s agent_uid=%s user_uid=%s",
            agent_id,
            channel_name,
            agent_uid,
            user_uid,
        )

        return {
            "agent_id": agent_id,
            "channel_name": channel_name,
            "status": "started",
            "language": voice_language,
            "persona": voice_persona,
            "stt": stt_name,
            "tts": tts_name,
        }

    async def stop(self, agent_id: str) -> None:
        """Stop a running agent. Falls back to the stateless client path."""
        if not agent_id or not str(agent_id).strip():
            raise ValueError("agent_id is required and cannot be empty")

        # Phase 6.3: PSTN calls end via telephony hangup, not RTC stop.
        if agent_id in self._telephony_ids:
            await self.hangup_call(agent_id)
            return

        session = self._sessions.pop(agent_id, None)
        if session:
            try:
                await session.stop()
                logger.info("Stopped Agora agent from active session agent_id=%s", agent_id)
                return
            except Exception:
                # Fall back to the stateless SDK path if the in-memory session is stale.
                logger.warning(
                    "Failed to stop Agora agent from active session; falling back to client.stop_agent agent_id=%s",
                    agent_id,
                    exc_info=True,
                )

        logger.info("Stopping Agora agent through client.stop_agent agent_id=%s", agent_id)
        await self.client.stop_agent(agent_id)

    def telephony_status(self) -> Dict[str, Any]:
        """PSTN readiness (plan.md 6.3) — env only, no cloud call."""
        return telephony_status_info()

    async def dial_call(
        self,
        to_number: str,
        from_number: Optional[str] = None,
        language: Optional[str] = None,
        persona: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Outbound PSTN call that joins the callee to a WeatherGPT voice agent.

        Requires the Telephony Beta (TELEPHONY_ENABLED + FROM_NUMBER +
        CUSTOMER_ID/SECRET); otherwise raises TelephonyDisabledError (501)
        with setup steps. Uses the SDK telephony.call SIP path with minimal
        channel properties — after the Beta grant, embed the full WeatherGPT
        STT/LLM/TTS pipeline config here so phone callers get the same
        Hinglish/Indic voice loop as web callers.
        """
        status = telephony_status_info()
        if not status["enabled"]:
            raise TelephonyDisabledError(TELEPHONY_SETUP_GUIDE)
        to = parse_e164_number(to_number, "toNumber")
        frm = parse_e164_number(from_number or os.getenv("TELEPHONY_FROM_NUMBER", ""), "fromNumber")

        channel_name = f"tel-{int(time.time())}-{random.randint(1000, 9999)}"
        sip_uid = random.randint(1000, 9999999)
        agent_rtc_uid = str(random.randint(10000000, 99999999))
        sip_token = generate_convo_ai_token(
            app_id=self.app_id,
            app_certificate=self.app_certificate,
            channel_name=channel_name,
            uid=sip_uid,
            token_expire=3600,
        )
        channel_token = generate_convo_ai_token(
            app_id=self.app_id,
            app_certificate=self.app_certificate,
            channel_name=channel_name,
            uid=int(agent_rtc_uid),
            token_expire=3600,
        )

        try:
            from agora_agent.telephony.types.call_telephony_request_properties import (
                CallTelephonyRequestProperties,
            )
            from agora_agent.telephony.types.call_telephony_request_sip import (
                CallTelephonyRequestSip,
            )
        except ImportError as e:
            raise RuntimeError(f"agora-agents SDK has no telephony support: {e}")

        sip = CallTelephonyRequestSip(
            to_number=to,
            from_number=frm,
            rtc_uid=str(sip_uid),
            rtc_token=sip_token,
        )
        properties = CallTelephonyRequestProperties(
            channel=channel_name,
            token=channel_token,
            agent_rtc_uid=agent_rtc_uid,
            remote_rtc_uids=[str(sip_uid)],
        )
        try:
            response = await self.client.telephony.call(
                self.app_id,
                name=f"wx-tel-{int(time.time())}",
                sip=sip,
                properties=properties,
            )
        except Exception:
            logger.exception("Telephony dial failed to_number=%s channel=%s", to, channel_name)
            raise

        agent_id = response.agent_id
        self._telephony_ids.add(agent_id)
        logger.info("Started telephony call agent_id=%s to=%s channel=%s", agent_id, to, channel_name)
        return {
            "agent_id": agent_id,
            "channel_name": channel_name,
            "to_number": to,
            "status": "calling",
            "language": normalize_language(language),
            "persona": normalize_persona(persona),
        }

    async def hangup_call(self, agent_id: str) -> None:
        """End a PSTN call (plan.md 6.3)."""
        if not agent_id or not str(agent_id).strip():
            raise ValueError("agent_id is required and cannot be empty")
        if not telephony_status_info()["enabled"]:
            raise TelephonyDisabledError(TELEPHONY_SETUP_GUIDE)
        await self.client.telephony.hangup(self.app_id, agent_id)
        self._telephony_ids.discard(agent_id)
        logger.info("Hung up telephony call agent_id=%s", agent_id)

    async def interrupt(self, agent_id: str) -> None:
        """Manually interrupt a speaking/thinking agent (plan.md 2.2 InterruptButton)."""
        if not agent_id or not str(agent_id).strip():
            raise ValueError("agent_id is required and cannot be empty")
        if agent_id in self._telephony_ids:
            raise ValueError(f"telephony call {agent_id}: RTC controls unavailable, use hangup")
        session = self._sessions.get(agent_id)
        if session is None:
            raise ValueError(f"unknown agent_id: {agent_id}")
        await session.interrupt()
        logger.info("Interrupted Agora agent agent_id=%s", agent_id)

    async def get_history(self, agent_id: str) -> Any:
        """Return conversation history for verification (plan.md 2.1: check turns)."""
        if not agent_id or not str(agent_id).strip():
            raise ValueError("agent_id is required and cannot be empty")
        if agent_id in self._telephony_ids:
            raise ValueError(f"telephony call {agent_id}: RTC controls unavailable, use hangup")
        session = self._sessions.get(agent_id)
        if session is None:
            raise ValueError(f"unknown agent_id: {agent_id}")
        return await session.get_history()

    async def get_turns(
        self,
        agent_id: str,
        page_index: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Any:
        """Return per-turn latency metrics (plan.md 2.1: target <1s ASR+LLM+TTS)."""
        if not agent_id or not str(agent_id).strip():
            raise ValueError("agent_id is required and cannot be empty")
        if agent_id in self._telephony_ids:
            raise ValueError(f"telephony call {agent_id}: RTC controls unavailable, use hangup")
        session = self._sessions.get(agent_id)
        if session is None:
            raise ValueError(f"unknown agent_id: {agent_id}")
        kwargs: Dict[str, Any] = {}
        if page_index is not None:
            kwargs["page_index"] = page_index
        if page_size is not None:
            kwargs["page_size"] = page_size
        return await session.get_turns(**kwargs)
