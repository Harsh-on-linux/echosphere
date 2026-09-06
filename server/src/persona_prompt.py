# -*- coding: utf-8 -*-
"""
VaayuMitra Persona Prompts — Phase 1.2 + 4.2
System prompts per persona: farmer / fisherman / disaster manager
See plan.md 4.2 for routing logic and research.md #6 for grounding rules.
"""

VAAYUMITRA_SYSTEM = """You are VaayuMitra, IMD-grounded voice assistant for farmers, fishermen, disaster managers.
You run via Agora Conversational AI Engine (SD-RTN + RTC/RTM + ASR->LLM->TTS) — never call LLM directly.

Rules:
1) Detect persona: farmer (rain/sowing/barish/crop), fisherman (sea/boat/machli/fishing), disaster (cyclone/storm/warning).
2) ALWAYS call resolve_location first to get district_id.
3) Call ONE IMD tool relevant to persona (farmer: get_rainfall_stats+get_agromet_advisory, fisherman: get_fishermen_warning+get_sea_area_bulletin, disaster: get_cyclone_track+get_all_india_warning).
4) Summarize in user's language, <30 words, plain, with source + timestamp. Never hallucinate numbers.
5) If resolve_location confidence <70, ask clarification: "Did you mean Thane or Thanjavur?"
6) If IMD data is fallback/mock, mention "IMD data busy, last update ...".
7) Keep tone helpful, short, and in user's spoken language (hi-IN, ta-IN, mr-IN, en-IN).

Free-tier: use credential_mode: managed (gpt-4o-mini + MiniMax) unless Indic needed via Sarvam BYOK.
"""

FARMER_PROMPT = """You serve farmers — prioritize get_crop_weather_advisory + get_rainfall_stats + get_agromet_advisory. Answer about sowing, rain, humidity, wind for crops. Use IMD districtrainfall and agromet advisory. Advise explicitly on chemical spraying safety, field drainage, and disease risks for crops like cotton, onion, paddy, soybean."""

FISHERMAN_PROMPT = """You serve fishermen — prioritize get_ocean_state_forecast + get_high_wave_alert + get_potential_fishing_zone + get_fishermen_warning + get_sea_area_bulletin + coastal_bulletin + port_warning. Answer about sea safety, wind speed, rough sea. Report wave height in meters, swell, sea condition, and safe distance for motorized boats and kattumarams."""

DISASTER_PROMPT = """You serve disaster managers — prioritize cyclone_track + cyclone_wind + cone + districtwarning. Summarize cyclone position, MSW, movement, cone, warnings succinctly."""

# For Agent init — greeting per language
GREETINGS = {
    "en-IN": "Hello, I am VaayuMitra. Which district's weather do you need?",
    "hi-IN": "Namaste, main VaayuMitra hun. Kaun se jile ka mausam janna hai?",
    "bho-IN": "Pranam, hum VaayuMitra haeen. Rauwa kavan jila ke mausam jaane ke chahat baani?",
    "ta-IN": "Vanakkam, naan VaayuMitra. Endha mavattam vaanilai vendum?",
    "mr-IN": "Namaskar, mi VaayuMitra ahe. Konatya jilhyacha hawaman havay?",
    "bn-IN": "Namaskar, ami VaayuMitra. Kon jelar abhawa jante chan?",
}

# Phase 4.1 — Indic pipeline languages (plan.md 4.1, research.md #12).
# en-IN runs managed (Deepgram + MiniMax, inside 300 free mins).
# hi/ta/mr/bn/bho-IN run Sarvam BYOK (STT+TTS) when SARVAM_API_KEY is set,
# else fall back to the managed English loop — never fail a session.
SUPPORTED_LANGUAGES = ("en-IN", "hi-IN", "bho-IN", "ta-IN", "mr-IN", "bn-IN")
INDIC_LANGUAGES = ("hi-IN", "bho-IN", "ta-IN", "mr-IN", "bn-IN")
DEFAULT_LANGUAGE = "en-IN"
SARVAM_SPEAKER = "priya"
SARVAM_MODEL = "bulbul:v3"

# Shorthand -> BCP-47 map for frontend dropdowns and API params.
_LANGUAGE_ALIASES = {
    "en": "en-IN", "english": "en-IN",
    "hi": "hi-IN", "hindi": "hi-IN",
    "bho": "bho-IN", "bhojpuri": "bho-IN",
    "ta": "ta-IN", "tamil": "ta-IN",
    "mr": "mr-IN", "marathi": "mr-IN",
    "bn": "bn-IN", "bengali": "bn-IN", "bangla": "bn-IN",
    "auto": "auto",
}

# turn_detection language per voice language (AGENTS.md #6: set together
# with asr.params.language). "auto" uses Sarvam `unknown` for STT and keeps
# VAD on en-US. Agora turn_detection supports bn-IN, en-IN, gu-IN, hi-IN, kn-IN,
# ta-IN, te-IN; unsupported Indic languages (mr-IN, bho-IN) safely map to hi-IN.
TURN_DETECTION_LANGUAGE = {
    "en-IN": "en-US",
    "hi-IN": "hi-IN",
    "bho-IN": "hi-IN",
    "ta-IN": "ta-IN",
    "mr-IN": "hi-IN",
    "bn-IN": "bn-IN",
    "auto": "en-US",
}

def normalize_language(language: str | None) -> str:
    """Map shorthand/empty input to a supported tag or 'auto'."""
    if not language:
        return DEFAULT_LANGUAGE
    key = language.strip().lower()
    canonical = {tag.lower(): tag for tag in SUPPORTED_LANGUAGES}
    canonical["auto"] = "auto"
    if key in canonical:
        return canonical[key]
    return _LANGUAGE_ALIASES.get(key, DEFAULT_LANGUAGE)

def get_greeting(language: str | None = None) -> str:
    """Greeting in the session language (plan.md 4.3 single_first)."""
    lang = normalize_language(language)
    if lang == "auto":
        return GREETINGS["hi-IN"]
    return GREETINGS.get(lang, GREETINGS[DEFAULT_LANGUAGE])

# Phase 4.3 — greeting & filler polish (plan.md 4.3).
# Single greeting on first join (interruptable, 200ms delay); static filler
# phrases cover IMD tool-call latency so the first 3 seconds feel seamless.
GREETING_CONFIGS = {"mode": "single_first", "interruptable": True, "delay_ms": 200}
FILLER_PHRASES = [
    "Ek second, IMD check kar raha hun...",
    "One moment, checking the latest IMD bulletin...",
    "Thoda samay dijiye, IMD data la raha hun...",
]
FILLER_WORDS = {"enable": True, "content": {"static_config": {"phrases": FILLER_PHRASES}}}

def get_system_prompt(persona: str = "general") -> str:
    base = VAAYUMITRA_SYSTEM
    if persona == "farmer":
        return base + "\n\nPersona hint: " + FARMER_PROMPT
    if persona == "fisherman":
        return base + "\n\nPersona hint: " + FISHERMAN_PROMPT
    if persona == "disaster":
        return base + "\n\nPersona hint: " + DISASTER_PROMPT
    return base

# Back-compat alias (pre-rebrand imports).
WEATHERGPT_SYSTEM = VAAYUMITRA_SYSTEM

# Phase 4.2 — persona-aware routing (plan.md 4.2).
# Pre-call persona picks the system-prompt hint + TTS rate; in-session the
# LLM re-detects per utterance (VAAYUMITRA_SYSTEM rule 1). Farmer speech is
# slowed to 0.9 for elders; disaster is slightly brisk (1.05).
PERSONAS = ("general", "farmer", "fisherman", "disaster")
DEFAULT_PERSONA = "general"
PERSONA_TTS_RATE = {"general": 1.0, "farmer": 0.9, "fisherman": 1.0, "disaster": 1.05}

PERSONA_KEYWORDS = {
    "disaster": ("cyclone", "storm", "toofan", "puyal", "warning", "alert",
                 "disaster", "flood", "baadh", "vellam", "evacuat"),
    "fisherman": ("fisherman", "fishing", "fish", "sea", "boat", "machli",
                  "machhi", "samudra", "samudram", "kadal", "meen", "wave", "swell", "lehar"),
    "farmer": ("farmer", "crop", "sowing", "sow", "barish", "baarish", "khet",
               "fasal", "kisan", "paddy", "dhaan", "beej", "harvest", "mazha", "spray", "keetnashak"),
}

def normalize_persona(persona: str | None) -> str:
    """Map empty/unknown input to a supported persona."""
    if not persona:
        return DEFAULT_PERSONA
    key = persona.strip().lower()
    return key if key in PERSONAS else DEFAULT_PERSONA

def detect_persona(text: str | None) -> str:
    """Keyword persona detection (priority: disaster > fisherman > farmer).

    Mirrors VAAYUMITRA_SYSTEM rule 1 so tests and the voice prompt agree.
    """
    if not text:
        return DEFAULT_PERSONA
    lowered = text.lower()
    for persona in ("disaster", "fisherman", "farmer"):
        if any(kw in lowered for kw in PERSONA_KEYWORDS[persona]):
            return persona
    return DEFAULT_PERSONA
