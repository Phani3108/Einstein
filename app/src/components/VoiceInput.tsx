import { useState, useCallback, useRef, useEffect } from "react";
import { Mic, MicOff } from "lucide-react";
import { useTranslation, getLanguage, VOICE_LANG_MAP } from "../lib/i18n";

interface SpeechRecognitionEvent {
  results: { [index: number]: { [index: number]: { transcript: string } }; length: number };
  resultIndex: number;
}

interface SpeechRecognitionInstance {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognitionInstance;
    webkitSpeechRecognition: new () => SpeechRecognitionInstance;
  }
}

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  className?: string;
  size?: number;
}

export function VoiceInput({ onTranscript, className = "", size = 16 }: VoiceInputProps) {
  const { t } = useTranslation();
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(true);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSupported(false);
    }
    return () => {
      recognitionRef.current?.abort();
    };
  }, []);

  const toggleListening = useCallback(() => {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = VOICE_LANG_MAP[getLanguage()] || "en-US";
    recognition.continuous = true;
    recognition.interimResults = false;

    recognition.onstart = () => setListening(true);

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const last = event.results[event.resultIndex];
      if (last?.[0]?.transcript) {
        onTranscript(last[0].transcript);
      }
    };

    recognition.onerror = (event: { error: string }) => {
      console.error("Speech recognition error:", event.error);
      setListening(false);
    };

    recognition.onend = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
  }, [listening, onTranscript]);

  if (!supported) {
    return (
      <button
        className={`icon-btn voice-btn unsupported ${className}`}
        title={t("voice.unsupported")}
        disabled
      >
        <MicOff size={size} />
      </button>
    );
  }

  return (
    <button
      className={`icon-btn voice-btn ${listening ? "listening" : ""} ${className}`}
      onClick={toggleListening}
      title={listening ? t("voice.stop") : t("voice.speak")}
    >
      {listening ? <Mic size={size} className="pulse-icon" /> : <Mic size={size} />}
    </button>
  );
}

/* Floating voice button for mobile/web */
export function FloatingVoiceButton({ onTranscript }: { onTranscript: (text: string) => void }) {
  const { t } = useTranslation();
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(true);
  const [permissionState, setPermissionState] = useState<"unknown" | "granted" | "denied" | "requesting">("unknown");
  const [transcript, setTranscript] = useState("");
  const [showPermissionToast, setShowPermissionToast] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) setSupported(false);
    return () => { recognitionRef.current?.abort(); };
  }, []);

  const requestMicPermission = useCallback(async (): Promise<boolean> => {
    try {
      setPermissionState("requesting");
      setShowPermissionToast(true);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Got permission - stop the tracks immediately (we just needed permission)
      stream.getTracks().forEach(track => track.stop());
      setPermissionState("granted");
      setShowPermissionToast(false);
      return true;
    } catch (err) {
      console.error("Microphone permission denied:", err);
      setPermissionState("denied");
      // Keep toast visible for a moment to show denied state
      setTimeout(() => setShowPermissionToast(false), 3000);
      return false;
    }
  }, []);

  const toggle = useCallback(async () => {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      if (transcript) {
        onTranscript(transcript);
        setTranscript("");
      }
      return;
    }

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;

    // Request mic permission first if not already granted
    if (permissionState !== "granted") {
      const granted = await requestMicPermission();
      if (!granted) return;
    }

    const r = new SR();
    r.lang = VOICE_LANG_MAP[getLanguage()] || "en-US";
    r.continuous = true;
    r.interimResults = true;

    r.onstart = () => { setListening(true); setTranscript(""); };
    r.onresult = (e: SpeechRecognitionEvent) => {
      let full = "";
      for (let i = 0; i < e.results.length; i++) {
        full += e.results[i]?.[0]?.transcript ?? "";
      }
      setTranscript(full);
    };
    r.onerror = (ev: { error: string }) => {
      console.error("Voice error:", ev.error);
      setListening(false);
    };
    r.onend = () => {
      setListening(false);
    };

    recognitionRef.current = r;
    r.start();
  }, [listening, transcript, onTranscript, permissionState, requestMicPermission]);

  if (!supported) return null;

  return (
    <>
      {/* Permission request toast */}
      {showPermissionToast && (
        <div className="mic-permission-toast">
          {permissionState === "requesting" ? (
            <>
              <div className="mic-toast-title">Microphone Access</div>
              <div className="mic-toast-desc">
                Please allow microphone access in the dialog that appears. Einstein processes voice locally on your device.
              </div>
            </>
          ) : permissionState === "denied" ? (
            <>
              <div className="mic-toast-title" style={{ color: "var(--red)" }}>Access Denied</div>
              <div className="mic-toast-desc">
                Microphone access was denied. To enable voice input, allow microphone access in your system settings.
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* Live transcript overlay */}
      {listening && transcript && (
        <div className="voice-overlay">
          <div className="voice-transcript">{transcript}</div>
          <div className="voice-hint">{t("voice.listening")}</div>
        </div>
      )}

      {/* Floating button */}
      <button
        className={`floating-voice-btn ${listening ? "active" : ""} ${permissionState === "requesting" ? "requesting" : ""}`}
        onClick={toggle}
        title={listening ? t("voice.stop") : t("voice.speak")}
      >
        {listening ? (
          <div className="voice-pulse">
            <Mic size={24} />
          </div>
        ) : (
          <Mic size={24} />
        )}
      </button>
    </>
  );
}
