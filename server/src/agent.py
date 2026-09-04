"""
Agent

High-level API for managing Agora Conversational AI Agents.
"""
import logging
import os
import time
from typing import Any, Dict, Optional

from agora_agent import Area, AsyncAgora
from agora_agent.agentkit import Agent as AgoraAgent
from agora_agent.agentkit.vendors import DeepgramSTT, MiniMaxTTS, OpenAI

try:
    from persona_prompt import GREETINGS, WEATHERGPT_SYSTEM
except ImportError:  # pragma: no cover - fallback when run from a different cwd
    from src.persona_prompt import GREETINGS, WEATHERGPT_SYSTEM  # type: ignore

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


def get_mcp_servers() -> Optional[list]:
    """Build llm.mcp_servers for Agora (plan.md 3.3, research.md #6).

    Agora calls POST {url} (JSON-RPC) when the LLM decides to use an IMD tool.
    URL must be public HTTPS in prod (plan.md 6.1); localhost works for tests
    to verify config shape. Returns None when unconfigured so managed-only
    sessions stay byte-identical to Phase 2.
    """
    explicit = (os.getenv("MCP_SERVER_URL") or "").strip()
    if explicit:
        url = explicit
    else:
        backend = (os.getenv("BACKEND_URL") or "").strip().rstrip("/")
        if not backend:
            return None
        url = f"{backend}/mcp"
    return [{"url": url, "transport": "streamable_http", "name": "imd"}]


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

        self.client = AsyncAgora(
            area=Area.US,
            app_id=self.app_id,
            app_certificate=self.app_certificate,
        )

        # Track active sessions by agent_id
        self._sessions: Dict[str, Any] = {}

    async def start(
        self,
        channel_name: str,
        agent_uid: int,
        user_uid: int,
        output_audio_codec: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start agent with the same default vendor chain as the Next.js quickstart."""
        if not channel_name or not str(channel_name).strip():
            raise ValueError("channel_name is required and cannot be empty")
        if agent_uid <= 0:
            raise ValueError("agent_uid is required and cannot be empty")
        if user_uid <= 0:
            raise ValueError("user_uid is required and cannot be empty")

        # Default managed path: DeepgramSTT + OpenAI + MiniMaxTTS (plan.md 2.1).
        # Managed = included in the $0.10/min Conv AI price, inside 300 free mins.
        # Phase 3.3: attach IMD MCP so the LLM can call resolve_location +
        # forecast/warning tools via POST {BACKEND_URL}/mcp (enable_tools below).
        mcp_servers = get_mcp_servers()
        llm_kwargs: Dict[str, Any] = dict(
            model="gpt-4o-mini",
            system_messages=[{"role": "system", "content": WEATHERGPT_SYSTEM}],
            greeting_message=self.greeting,
            failure_message=self.failure_message,
            max_history=WEATHERGPT_MAX_HISTORY,
            max_tokens=1024,
            temperature=0.7,
            top_p=0.95,
        )
        if mcp_servers is not None:
            llm_kwargs["mcp_servers"] = mcp_servers
        llm = OpenAI(**llm_kwargs)
        stt = DeepgramSTT(model="nova-3", language="en")
        tts = MiniMaxTTS(model="speech_2_6_turbo", voice_id="English_captivating_female1")

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
            "audio_scenario": "chorus",  # web client → ultra-low-latency chorus profile
            "data_channel": "rtm",
            "enable_error_message": True,
            "enable_metrics": True,
        }
        if isinstance(output_audio_codec, str) and output_audio_codec.strip():
            parameters["output_audio_codec"] = output_audio_codec.strip()

        agora_agent = AgoraAgent(
            client=self.client,
            instructions=WEATHERGPT_SYSTEM,
            greeting=self.greeting,
            failure_message=self.failure_message,
            max_history=WEATHERGPT_MAX_HISTORY,
            turn_detection={
                "language": "en-US",
                "mode": "default",
                "config": {
                    "speech_threshold": 0.5,
                    "start_of_speech": {
                        "mode": "vad",
                        "vad_config": {
                            "interrupt_duration_ms": 160,
                            "prefix_padding_ms": 300,
                        },
                    },
                    "end_of_speech": {
                        "mode": "vad",
                        "vad_config": {
                            "silence_duration_ms": 480,
                        },
                    },
                },
            },
            interruption={"enable": True, "mode": "start_of_speech"},
            advanced_features={"enable_rtm": True, "enable_tools": True},
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
        }

    async def stop(self, agent_id: str) -> None:
        """Stop a running agent. Falls back to the stateless client path."""
        if not agent_id or not str(agent_id).strip():
            raise ValueError("agent_id is required and cannot be empty")

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

    async def interrupt(self, agent_id: str) -> None:
        """Manually interrupt a speaking/thinking agent (plan.md 2.2 InterruptButton)."""
        if not agent_id or not str(agent_id).strip():
            raise ValueError("agent_id is required and cannot be empty")
        session = self._sessions.get(agent_id)
        if session is None:
            raise ValueError(f"unknown agent_id: {agent_id}")
        await session.interrupt()
        logger.info("Interrupted Agora agent agent_id=%s", agent_id)

    async def get_history(self, agent_id: str) -> Any:
        """Return conversation history for verification (plan.md 2.1: check turns)."""
        if not agent_id or not str(agent_id).strip():
            raise ValueError("agent_id is required and cannot be empty")
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
        session = self._sessions.get(agent_id)
        if session is None:
            raise ValueError(f"unknown agent_id: {agent_id}")
        kwargs: Dict[str, Any] = {}
        if page_index is not None:
            kwargs["page_index"] = page_index
        if page_size is not None:
            kwargs["page_size"] = page_size
        return await session.get_turns(**kwargs)
