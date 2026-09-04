"use client";

import { useEffect, useState } from "react";

const ASR_LANGUAGES = [
  { value: "en-IN", label: "English (India)" },
  { value: "hi-IN", label: "Hindi" },
  { value: "ta-IN", label: "Tamil" },
  { value: "mr-IN", label: "Marathi" },
  { value: "bn-IN", label: "Bengali" },
] as const;

const TTS_VOICES = [
  { value: "English_captivating_female1", label: "MiniMax English female" },
  { value: "anushka", label: "Sarvam Anushka (Indic, Phase 4)" },
] as const;

const STORAGE_KEY = "weathergpt.voice-settings";

export type VoiceSettings = {
  asrLanguage: string;
  ttsVoice: string;
};

function loadSettings(): VoiceSettings {
  if (typeof window === "undefined") {
    return { asrLanguage: "en-IN", ttsVoice: TTS_VOICES[0].value };
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<VoiceSettings>;
      return {
        asrLanguage: parsed.asrLanguage ?? "en-IN",
        ttsVoice: parsed.ttsVoice ?? TTS_VOICES[0].value,
      };
    }
  } catch {
    // Corrupt storage: fall through to defaults.
  }
  return { asrLanguage: "en-IN", ttsVoice: TTS_VOICES[0].value };
}

/**
 * VoiceSettingsPanel — switch ASR language / TTS voice (plan.md 2.2).
 * Phase 2 stores the pre-call preference; Phase 4 applies it live via
 * Sarvam BYOK without restarting the channel.
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
    <fieldset
      className="mx-auto flex w-[min(92vw,26.25rem)] flex-col gap-3 rounded-[20px] border border-border bg-card/20 px-5 py-4 text-left"
      aria-label="Voice settings"
    >
      <legend className="px-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Voice settings
      </legend>
      <label className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
        ASR language
        <select
          className="h-9 rounded-md border border-border bg-background px-2 text-sm text-foreground"
          value={settings.asrLanguage}
          onChange={(event) =>
            setSettings((prev) => ({ ...prev, asrLanguage: event.target.value }))
          }
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
      <p className="text-[11px] leading-4 text-muted-foreground">
        Phase 2 runs the managed English loop. Indic voices activate in Phase 4
        via Sarvam BYOK.
      </p>
    </fieldset>
  );
}
