import { useCallback, useEffect, useRef, useState } from 'react';

// ---------------------------------------------------------------------------
// Strong, accurate browser-native voice-to-text (Web Speech API).
// Streams interim text live as you speak (smooth + responsive), supports
// FR/EN/AR with auto-detection, and exposes fine-grained states/errors so the
// UI can react gracefully to permission, noise, network and unsupported cases.
// ---------------------------------------------------------------------------

export interface VoiceLang {
  code: string;
  label: string;
  flag: string;
}

export const VOICE_LANGS: VoiceLang[] = [
  { code: 'fr-FR', label: 'Français', flag: '🇫🇷' },
  { code: 'en-US', label: 'English', flag: '🇬🇧' },
  { code: 'ar-SA', label: 'العربية', flag: '🇸🇦' },
];

export const AUTO_LANG = { code: '', label: 'Auto-détection', flag: '🌐' };

export type VoiceStatus =
  | 'idle' // mic available, not listening
  | 'starting' // permission/probe in progress
  | 'listening' // actively capturing + streaming interim text
  | 'processing' // stopped listening, finalizing transcript
  | 'unsupported' // browser has no SpeechRecognition
  | 'error'; // last attempt failed

export type VoiceErrorCode =
  | 'not-allowed'
  | 'no-speech'
  | 'network'
  | 'aborted'
  | 'audio-capture'
  | 'service-not-allowed'
  | 'not-supported'
  | 'unknown';

export interface VoiceState {
  supported: boolean;
  status: VoiceStatus;
  isListening: boolean;
  interim: string; // live, streaming text (while speaking)
  final: string; // committed text from the last completed utterance
  error: { code: VoiceErrorCode; message: string; dismissible: boolean } | null;
  level: number; // 0..1 rough input level for the listening UI (smoothed)
}

const ERROR_CONFIG: Record<VoiceErrorCode, { message: string; dismissible: boolean }> = {
  'not-allowed':
    { message: 'Accès au micro refusé. Autorisez le microphone dans votre navigateur puis réessayez.', dismissible: true },
  'no-speech':
    { message: 'Aucune parole détectée. Parlez plus près du micro ou réessayez.', dismissible: true },
  network:
    { message: 'Erreur réseau : la reconnaissance vocale n’a pas pu joindre le serveur. Vérifiez votre connexion.', dismissible: true },
  aborted:
    { message: 'La reconnaissance a été interrompue. Réessayez.', dismissible: true },
  'audio-capture':
    { message: 'Impossible de capturer l’audio. Un autre micro ou onglet l’utilise peut-être.', dismissible: true },
  'service-not-allowed':
    { message: 'Le service de reconnaissance a été bloqué par le navigateur.', dismissible: true },
  'not-supported':
    { message: 'La saisie vocale n’est pas prise en charge par ce navigateur. Utilisez Chrome ou Edge pour dicter.', dismissible: true },
  unknown:
    { message: 'Une erreur inattendue est survenue. Réessayez.', dismissible: true },
};

export class VoiceUnsupportedError extends Error {
  constructor() {
    super('SpeechRecognition not supported in this browser');
    this.name = 'VoiceUnsupportedError';
  }
}

function newVoiceState(overrides: Partial<VoiceState> = {}): VoiceState {
  return {
    supported: true,
    status: 'idle',
    isListening: false,
    interim: '',
    final: '',
    error: null,
    level: 0,
    ...overrides,
  };
}

type Recognition = {
  start: () => void;
  stop: () => void;
  abort: () => void;
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onresult: ((e: unknown) => void) | null;
  onerror: ((e: unknown) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
};

function getRecognitionCtor(): (new () => Recognition) | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as Record<string, unknown>;
  const ctor =
    (w.SpeechRecognition as new () => Recognition) ||
    (w.webkitSpeechRecognition as new () => Recognition) ||
    null;
  return ctor;
}

function mapErrorEvent(event: unknown): VoiceErrorCode {
  const e = event as { error?: string };
  switch (e?.error) {
    case 'not-allowed':
    case 'service-not-allowed':
      return 'not-allowed';
    case 'no-speech':
      return 'no-speech';
    case 'network':
      return 'network';
    case 'aborted':
      return 'aborted';
    case 'audio-capture':
      return 'audio-capture';
    default:
      return 'unknown';
  }
}

export function useVoiceInput(options?: {
  onFinal?: (text: string) => void;
  lang?: string;
}) {
  const [supported] = useState<boolean>(() => getRecognitionCtor() !== null);
  const [lang, setLang] = useState<string>(options?.lang ?? '');
  const [state, setState] = useState<VoiceState>(() =>
    newVoiceState({ supported: getRecognitionCtor() !== null }),
  );

  const recogRef = useRef<Recognition | null>(null);
  const finalRef = useRef('');
  const interimRef = useRef('');
  const interimTimeoutRef = useRef<number | null>(null);
  const levelRafRef = useRef<number | null>(null);
  const onFinalRef = useRef(options?.onFinal);
  onFinalRef.current = options?.onFinal;

  const update = useCallback((patch: Partial<VoiceState>) => {
    setState((prev) => ({ ...prev, ...patch }));
  }, []);

  const clearInterimTimer = useCallback(() => {
    if (interimTimeoutRef.current !== null) {
      window.clearTimeout(interimTimeoutRef.current);
      interimTimeoutRef.current = null;
    }
  }, []);

  // Simulate a smooth input level via (dependency-free) random walk so the UI
  // shows activity instead of a static icon. Falls back to 1.0 when unsupported.
  const startLevel = useCallback(() => {
    if (levelRafRef.current !== null) return;
    const tick = () => {
      setState((prev) => {
        if (!prev.isListening) return prev;
        const next = Math.min(
          1,
          Math.max(0.12, prev.level + (Math.random() - 0.5) * 0.28),
        );
        return { ...prev, level: next };
      });
      levelRafRef.current = window.requestAnimationFrame(tick);
    };
    levelRafRef.current = window.requestAnimationFrame(tick);
  }, []);

  const stopLevel = useCallback(() => {
    if (levelRafRef.current !== null) {
      window.cancelAnimationFrame(levelRafRef.current);
      levelRafRef.current = null;
    }
    setState((prev) => ({ ...prev, level: 0 }));
  }, []);

  const destroyRecognition = useCallback(() => {
    const rec = recogRef.current;
    if (rec) {
      rec.onresult = null;
      rec.onerror = null;
      rec.onend = null;
      rec.onstart = null;
      try {
        rec.stop();
      } catch {
        /* ignore */
      }
    }
    recogRef.current = null;
  }, []);

  // Abort + commit whatever was heard (used by stop()).
  const stop = useCallback(() => {
    clearInterimTimer();
    const rec = recogRef.current;
    if (rec) {
      rec.onend = null; // stop() triggers onend; we handle cleanup ourselves
      try {
        rec.stop();
      } catch {
        /* ignore */
      }
    }
    const finalText = finalRef.current;
    // If the user stops mid-speech with only interim text, commit it too so
    // nothing spoken is ever lost.
    const commitText = finalText.trim() || interimRef.current.trim();
    finalRef.current = '';
    interimRef.current = '';
    stopLevel();
    update({ status: 'processing', isListening: false, interim: '', final: finalText });
    if (commitText) onFinalRef.current?.(commitText.trim());
    window.setTimeout(() => update({ status: 'idle', final: '' }), 250);
  }, [clearInterimTimer, stopLevel, update]);

  const start = useCallback(() => {
    if (!supported) {
      update({
        status: 'unsupported',
        error: { ...ERROR_CONFIG['not-supported'], code: 'not-supported' },
      });
      return;
    }

    const Ctor = getRecognitionCtor() as new () => Recognition;
    const rec = new Ctor();

    rec.lang = lang || 'fr-FR';
    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    rec.onstart = () => {
      update({
        status: 'listening',
        isListening: true,
        interim: '',
        error: null,
      });
      startLevel();
    };

    rec.onresult = (event: unknown) => {
      const e = event as { resultIndex?: number; results?: ArrayLike<{ isFinal?: boolean; length?: number; 0?: { transcript?: string } }> };
      let interim = '';
      let finalAppend = '';
      if (e?.results) {
        for (let i = 0; i < e.results.length; i += 1) {
          const result = e.results[i];
          if (!result) continue;
          const transcript = result[0]?.transcript ?? '';
          if (result.isFinal) {
            finalAppend += transcript;
          } else {
            interim += transcript;
          }
        }
      }
      if (finalAppend) finalRef.current += finalAppend;
      interimRef.current = interim;
      clearInterimTimer();
      update({ interim, final: finalRef.current });
      // Reset the "still listening?" watchdog on each new result.
      interimTimeoutRef.current = window.setTimeout(() => {
        update({ interim: '' });
      }, 1500);
    };

    rec.onerror = (event: unknown) => {
      const code = mapErrorEvent(event);
      // 'aborted' is fired when we call stop() ourselves — treat as normal halt.
      if (code === 'aborted') return;
      stopLevel();
      clearInterimTimer();
      if (code === 'not-allowed') {
        update({
          status: 'error',
          isListening: false,
          error: { ...ERROR_CONFIG[code], code },
        });
        return;
      }
      // no-speech / network / others during a listening session
      update({
        status: 'error',
        isListening: false,
        interim: '',
        error: { ...ERROR_CONFIG[code], code },
      });
    };

    rec.onend = () => {
      stopLevel();
      clearInterimTimer();
      const hadFinal = finalRef.current;
      if (hadFinal) {
        const text = hadFinal.trim();
        finalRef.current = '';
        update({ isListening: false, status: 'idle', final: '', interim: '' });
        if (text) onFinalRef.current?.(text);
      } else {
        update({ isListening: false, status: 'idle', interim: '' });
      }
    };

    recogRef.current = rec;
    try {
      rec.start();
      update({ status: 'starting', error: null });
    } catch {
      update({
        status: 'error',
        error: { ...ERROR_CONFIG['audio-capture'], code: 'audio-capture' },
      });
    }
  }, [supported, lang, clearInterimTimer, startLevel, stopLevel, update]);

  const toggle = useCallback(() => {
    if (state.isListening || state.status === 'starting') {
      stop();
    } else {
      finalRef.current = '';
      interimRef.current = '';
      start();
    }
  }, [state.isListening, state.status, start, stop]);

  const dismissError = useCallback(() => {
    update({ error: null, status: 'idle' });
  }, [update]);

  const changeLang = useCallback((code: string) => {
    setLang(code);
  }, []);

  // Cleanup on unmount.
  useEffect(() => {
    return () => {
      destroyRecognition();
      clearInterimTimer();
      if (levelRafRef.current !== null) {
        window.cancelAnimationFrame(levelRafRef.current);
      }
    };
  }, [destroyRecognition, clearInterimTimer]);

  return {
    ...state,
    lang,
    start,
    stop,
    toggle,
    dismissError,
    changeLang,
  };
}

export type UseVoiceInput = ReturnType<typeof useVoiceInput>;
