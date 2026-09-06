"use client";

import { useEffect, useState } from "react";

const ASR_LANGUAGES = [
  { value: "en-IN", label: "English (India)" },
  { value: "hi-IN", label: "Hindi (हिंदी)" },
  { value: "bho-IN", label: "Bhojpuri (भोजपुरी)" },
  { value: "ta-IN", label: "Tamil (தமிழ்)" },
  { value: "mr-IN", label: "Marathi (मराठी)" },
  { value: "bn-IN", label: "Bengali (বাংলা)" },
] as const;

const TTS_VOICES = [
  { value: "English_captivating_female1", label: "MiniMax English female" },
  { value: "priya", label: "Sarvam Priya (Indic bulbul:v3)" },
  { value: "aditya", label: "Sarvam Aditya (Indic bulbul:v3)" },
] as const;

const PERSONAS = [
  { value: "general", label: "General" },
  { value: "farmer", label: "Farmer (rain/sowing)" },
  { value: "fisherman", label: "Fisherman (sea safety)" },
  { value: "disaster", label: "Disaster manager" },
] as const;

const STORAGE_KEY = "vaayumitra.voice-settings";
const LEGACY_STORAGE_KEY = "weathergpt.voice-settings";

export type VoiceSettings = {
  asrLanguage: string;
  ttsVoice: string;
  persona: string;
};

const DEFAULT_SETTINGS: VoiceSettings = {
  asrLanguage: "en-IN",
  ttsVoice: TTS_VOICES[0].value,
  persona: "general",
};

function loadSettings(): VoiceSettings {
  if (typeof window === "undefined") {
    return { ...DEFAULT_SETTINGS };
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY) ?? window.localStorage.getItem(LEGACY_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<VoiceSettings>;
      const storedVoice = parsed.ttsVoice === "anushka" ? "priya" : (parsed.ttsVoice ?? DEFAULT_SETTINGS.ttsVoice);
      return {
        asrLanguage: parsed.asrLanguage ?? DEFAULT_SETTINGS.asrLanguage,
        ttsVoice: storedVoice,
        persona: parsed.persona ?? DEFAULT_SETTINGS.persona,
      };
    }
  } catch {
    // Corrupt storage: fall through to defaults.
  }
  return { ...DEFAULT_SETTINGS };
}

/**
 * VoiceSettingsPanel — switch ASR language / TTS voice / persona (plan.md 2.2, 4.2).
 * Phase 4 sends the pre-call preference with startAgent: Indic languages use
 * Sarvam BYOK when the server has a key, else the managed English loop.
 */
export function VoiceSettingsPanel({
  onChange,
}: {
  onChange?: (settings: VoiceSettings) => void;
}) {
  const [settings, setSettings] = useState<VoiceSettings>(loadSettings);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch {
      // Storage unavailable (private mode): settings still apply to this session.
    }
    onChange?.(settings);
  }, [settings, onChange]);

  return (
    <section
      className="flex w-full flex-col gap-3 rounded-3xl border border-border bg-card/20 px-5 py-4 text-left"
      aria-label="Voice settings"
    >
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Voice settings
      </h2>
      <label className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
        ASR language
        <select
          className="h-9 rounded-md border border-border bg-background px-2 text-sm text-foreground"
          value={settings.asrLanguage}
          onChange={(event) => {
            const nextLang = event.target.value;
            const isIndic = nextLang !== "en-IN";
            setSettings((prev) => ({
              ...prev,
              asrLanguage: nextLang,
              ttsVoice: isIndic ? "priya" : prev.ttsVoice,
            }));
          }}
          aria-label="ASR language"
        >
          {ASR_LANGUAGES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
        TTS voice
        <select
          className="h-9 rounded-md border border-border bg-background px-2 text-sm text-foreground"
          value={settings.ttsVoice}
          onChange={(event) =>
            setSettings((prev) => ({ ...prev, ttsVoice: event.target.value }))
          }
          aria-label="TTS voice"
        >
          {TTS_VOICES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
        Persona
        <select
          className="h-9 rounded-md border border-border bg-background px-2 text-sm text-foreground"
          value={settings.persona}
          onChange={(event) =>
            setSettings((prev) => ({ ...prev, persona: event.target.value }))
          }
          aria-label="Persona"
        >
          {PERSONAS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <p className="text-[11px] leading-4 text-muted-foreground">
        Indic languages use Sarvam BYOK when the server has a key, else the
        managed English loop. Persona tunes the prompt and speech rate.
      </p>
    </section>
  );
}
