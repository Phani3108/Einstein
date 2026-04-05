import { useState, useCallback } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import { useTranslation, LANGUAGES, setLanguage as setGlobalLanguage } from "../lib/i18n";
import type { Language } from "../lib/i18n";
import {
  Brain,
  FolderOpen,
  Plus,
  ChevronRight,
  ChevronLeft,
  Check,
  Sparkles,
  Globe,
  Palette,
  Cpu,
  Keyboard,
  ArrowRight,
  Search,
} from "lucide-react";
import { homeDir } from "@tauri-apps/api/path";
import { open } from "@tauri-apps/plugin-dialog";

type OnboardStep = "welcome" | "language" | "vault" | "preferences" | "ready";

const STEPS: OnboardStep[] = ["welcome", "language", "vault", "preferences", "ready"];

function validatePath(path: string): string | null {
  if (!path || !path.trim()) {
    return "Please enter a vault path";
  }
  if (path.trim() !== path && path.trim().length === 0) {
    return "Path cannot be only whitespace";
  }
  return null;
}

export function WelcomeScreen() {
  const { dispatch } = useApp();
  const { t } = useTranslation();
  const [step, setStep] = useState<OnboardStep>("welcome");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Onboarding state
  const [selectedLang, setSelectedLang] = useState<Language>("en");
  const [vaultPath, setVaultPath] = useState("");
  const [vaultName, setVaultName] = useState("");
  const [theme, setTheme] = useState<"dark" | "light" | "warm">("dark");
  const [aiMode, setAiMode] = useState<"local" | "cloud" | "none">("local");

  const stepIndex = STEPS.indexOf(step);

  const expandPath = useCallback(async (path: string): Promise<string> => {
    if (path.startsWith("~")) {
      try {
        const home = await homeDir();
        return path.replace("~", home.replace(/\/$/, ""));
      } catch {
        return path.replace("~", "/Users/user");
      }
    }
    return path;
  }, []);

  const handleBrowse = useCallback(async () => {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: "Select Vault Folder",
      });
      if (selected) {
        setVaultPath(selected as string);
        setError(null);
      }
    } catch (err) {
      console.error("Browse failed:", err);
    }
  }, []);

  const goNext = useCallback(() => {
    const idx = STEPS.indexOf(step);
    if (idx < STEPS.length - 1) setStep(STEPS[idx + 1]);
  }, [step]);

  const goBack = useCallback(() => {
    const idx = STEPS.indexOf(step);
    if (idx > 0) setStep(STEPS[idx - 1]);
  }, [step]);

  const handleLanguageSelect = useCallback((lang: Language) => {
    setSelectedLang(lang);
    setGlobalLanguage(lang);
  }, []);

  const handleOpenExistingVault = useCallback(async () => {
    const pathError = validatePath(vaultPath);
    if (pathError) {
      setError(pathError);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const expanded = await expandPath(vaultPath.trim());
      const notes = await api.openVault(expanded);
      // Save preferences
      try {
        await api.setConfig("theme", theme);
        await api.setConfig("ai_mode", aiMode);
        await api.setConfig("language", selectedLang);
      } catch {}
      dispatch({ type: "SET_VAULT", path: expanded, notes });
      dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
    } catch (err) {
      setError(typeof err === "string" ? err : String(err));
    } finally {
      setLoading(false);
    }
  }, [vaultPath, expandPath, dispatch, theme, aiMode, selectedLang]);

  const handleCreateVault = useCallback(async () => {
    const pathError = validatePath(vaultPath);
    if (pathError) {
      setError(pathError);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const expanded = await expandPath(vaultPath.trim());
      const notes = await api.openVault(expanded);

      // Save preferences
      try {
        await api.setConfig("theme", theme);
        await api.setConfig("ai_mode", aiMode);
        await api.setConfig("language", selectedLang);
      } catch {}

      // Create welcome note
      const welcomeNote = await api.saveNote(
        "welcome.md",
        vaultName || "Welcome to Einstein",
        `# Welcome to Einstein

Your AI-powered second brain is ready.

## Getting Started

- **Create notes** using the + button or press \`\u2318N\`
- **Link notes** using [[wikilinks]] \u2014 just type \`[[\` and the note name
- **Search** with \`\u2318P\` to find anything instantly
- **Daily notes** are created with the calendar button
- **AI entities** are extracted automatically when you save

## How it Works

Einstein combines plain markdown notes with powerful AI:

- Every note is a \`.md\` file on your disk \u2014 no vendor lock-in
- AI automatically extracts people, places, topics, and more
- Semantic search finds notes by meaning, not just keywords
- The knowledge graph shows connections between your ideas

Happy thinking!
`,
        { type: "welcome" }
      );

      dispatch({
        type: "SET_VAULT",
        path: expanded,
        notes: [welcomeNote, ...notes],
      });
      dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
    } catch (err) {
      setError(typeof err === "string" ? err : String(err));
    } finally {
      setLoading(false);
    }
  }, [vaultPath, vaultName, expandPath, dispatch, theme, aiMode, selectedLang]);

  const handleQuickOpen = useCallback(async () => {
    const pathError = validatePath(vaultPath);
    if (pathError) {
      setError(pathError);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const expanded = await expandPath(vaultPath.trim());
      const notes = await api.openVault(expanded);
      dispatch({ type: "SET_VAULT", path: expanded, notes });
      dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
    } catch (err) {
      setError(typeof err === "string" ? err : String(err));
    } finally {
      setLoading(false);
    }
  }, [vaultPath, expandPath, dispatch]);

  return (
    <div className="welcome-screen">
      {/* Progress bar */}
      {step !== "welcome" && (
        <div className="onboard-progress">
          {STEPS.slice(1).map((s, i) => (
            <div
              key={s}
              className={`progress-dot ${
                i < stepIndex ? "complete" : i === stepIndex - 1 ? "active" : ""
              }`}
            />
          ))}
        </div>
      )}

      {/* Step: Welcome */}
      {step === "welcome" && (
        <div className="welcome-card onboard-card">
          <div className="welcome-logo">
            <Brain size={42} color="white" />
          </div>
          <h1>{t("welcome.title")}</h1>
          <p className="subtitle">{t("welcome.subtitle")}</p>

          {error && <div className="welcome-error">{error}</div>}

          <div className="welcome-buttons">
            <button className="btn-primary" onClick={() => setStep("language")} disabled={loading}>
              <Sparkles size={16} />
              {t("welcome.getStarted")}
              <ChevronRight size={14} />
            </button>
          </div>

          <div className="welcome-divider">
            <span>{t("welcome.or")}</span>
          </div>

          <div className="quick-open-section">
            <label className="input-label">{t("welcome.openExisting")}</label>
            <div className="quick-open-row">
              <input
                type="text"
                className="onboard-input"
                placeholder="~/Documents/my-vault"
                value={vaultPath}
                onChange={(e) => { setVaultPath(e.target.value); setError(null); }}
                onKeyDown={(e) => e.key === "Enter" && handleQuickOpen()}
              />
              <button
                className="btn-secondary"
                onClick={handleBrowse}
                title="Browse for folder"
                style={{ minWidth: "auto", padding: "8px 10px" }}
              >
                <Search size={14} />
              </button>
              <button className="btn-secondary" onClick={handleQuickOpen} disabled={loading || !vaultPath.trim()}>
                <FolderOpen size={14} />
                {loading ? "..." : "Open"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step: Language */}
      {step === "language" && (
        <div className="welcome-card onboard-card">
          <div className="step-icon">
            <Globe size={28} />
          </div>
          <h2>{t("onboard.step1.title")}</h2>
          <p className="step-desc">{t("onboard.step1.desc")}</p>

          <div className="language-grid">
            {LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                className={`language-option ${selectedLang === lang.code ? "selected" : ""}`}
                onClick={() => handleLanguageSelect(lang.code)}
              >
                <span className="lang-flag">{lang.flag}</span>
                <span className="lang-name">{lang.nativeName}</span>
                <span className="lang-english">{lang.name}</span>
                {selectedLang === lang.code && <Check size={14} className="lang-check" />}
              </button>
            ))}
          </div>

          <div className="onboard-nav">
            <button className="btn-ghost" onClick={goBack}>
              <ChevronLeft size={14} /> {t("onboard.back")}
            </button>
            <button className="btn-primary" onClick={goNext}>
              {t("onboard.next")} <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Step: Vault */}
      {step === "vault" && (
        <div className="welcome-card onboard-card">
          <div className="step-icon">
            <FolderOpen size={28} />
          </div>
          <h2>{t("onboard.step2.title")}</h2>
          <p className="step-desc">{t("onboard.step2.desc")}</p>

          {error && <div className="welcome-error">{error}</div>}

          <div className="form-group">
            <label className="input-label">{t("onboard.step2.vaultName")}</label>
            <input
              type="text"
              className="onboard-input"
              placeholder={t("onboard.step2.vaultNamePlaceholder")}
              value={vaultName}
              onChange={(e) => setVaultName(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="input-label">{t("onboard.step2.pathLabel")}</label>
            <div className="quick-open-row">
              <input
                type="text"
                className="onboard-input"
                placeholder={t("onboard.step2.pathPlaceholder")}
                value={vaultPath}
                onChange={(e) => { setVaultPath(e.target.value); setError(null); }}
                onKeyDown={(e) => e.key === "Enter" && goNext()}
              />
              <button
                className="btn-secondary"
                onClick={handleBrowse}
                title="Browse for folder"
                style={{ minWidth: "auto", padding: "8px 12px" }}
              >
                <FolderOpen size={14} />
                Browse
              </button>
            </div>
            <span className="input-hint">{t("onboard.step2.pathHint")}</span>
          </div>

          <div className="onboard-nav">
            <button className="btn-ghost" onClick={goBack}>
              <ChevronLeft size={14} /> {t("onboard.back")}
            </button>
            <button className="btn-primary" onClick={goNext} disabled={!vaultPath.trim()}>
              {t("onboard.next")} <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Step: Preferences */}
      {step === "preferences" && (
        <div className="welcome-card onboard-card">
          <div className="step-icon">
            <Palette size={28} />
          </div>
          <h2>{t("onboard.step3.title")}</h2>
          <p className="step-desc">{t("onboard.step3.desc")}</p>

          <div className="pref-section">
            <label className="input-label">{t("onboard.step3.theme")}</label>
            <div className="pref-options">
              {([
                { key: "dark" as const, label: t("onboard.step3.themeDark"), preview: "#1a1a2e" },
                { key: "light" as const, label: t("onboard.step3.themeLight"), preview: "#f5f5f5" },
                { key: "warm" as const, label: t("onboard.step3.themeWarm"), preview: "#2a2520" },
              ]).map((opt) => (
                <button
                  key={opt.key}
                  className={`pref-card ${theme === opt.key ? "selected" : ""}`}
                  onClick={() => setTheme(opt.key)}
                >
                  <div className="theme-preview" style={{ background: opt.preview }} />
                  <span>{opt.label}</span>
                  {theme === opt.key && <Check size={12} />}
                </button>
              ))}
            </div>
          </div>

          <div className="pref-section">
            <label className="input-label">{t("onboard.step3.aiMode")}</label>
            <div className="ai-options">
              {([
                { key: "local" as const, icon: <Cpu size={16} />, label: t("onboard.step3.aiLocal"), desc: t("onboard.step3.aiLocalDesc") },
                { key: "cloud" as const, icon: <Sparkles size={16} />, label: t("onboard.step3.aiCloud"), desc: t("onboard.step3.aiCloudDesc") },
                { key: "none" as const, icon: <Keyboard size={16} />, label: t("onboard.step3.aiNone"), desc: t("onboard.step3.aiNoneDesc") },
              ]).map((opt) => (
                <button
                  key={opt.key}
                  className={`ai-option-card ${aiMode === opt.key ? "selected" : ""}`}
                  onClick={() => setAiMode(opt.key)}
                >
                  <div className="ai-option-icon">{opt.icon}</div>
                  <div className="ai-option-text">
                    <div className="ai-option-label">{opt.label}</div>
                    <div className="ai-option-desc">{opt.desc}</div>
                  </div>
                  {aiMode === opt.key && <Check size={14} className="ai-check" />}
                </button>
              ))}
            </div>
          </div>

          <div className="onboard-nav">
            <button className="btn-ghost" onClick={goBack}>
              <ChevronLeft size={14} /> {t("onboard.back")}
            </button>
            <button className="btn-primary" onClick={goNext}>
              {t("onboard.next")} <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Step: Ready */}
      {step === "ready" && (
        <div className="welcome-card onboard-card">
          <div className="step-icon ready-icon">
            <Check size={28} />
          </div>
          <h2>{t("onboard.step4.title")}</h2>
          <p className="step-desc">{t("onboard.step4.desc")}</p>

          {error && <div className="welcome-error">{error}</div>}

          <div className="tips-list">
            {[
              t("onboard.step4.tip1"),
              t("onboard.step4.tip2"),
              t("onboard.step4.tip3"),
              t("onboard.step4.tip4"),
              t("onboard.step4.tip5"),
            ].map((tip, i) => (
              <div key={i} className="tip-item">
                <ArrowRight size={12} />
                <span>{tip}</span>
              </div>
            ))}
          </div>

          <div className="onboard-nav" style={{ marginTop: 24 }}>
            <button className="btn-ghost" onClick={goBack}>
              <ChevronLeft size={14} /> {t("onboard.back")}
            </button>
            <button
              className="btn-primary btn-lg"
              onClick={handleCreateVault}
              disabled={loading || !vaultPath.trim()}
            >
              {loading ? (
                <div className="loading-spinner" />
              ) : (
                <Plus size={16} />
              )}
              {loading ? t("general.loading") : t("onboard.step4.launch")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
