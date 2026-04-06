/* ================================================================
   Einstein Internationalization (i18n) System
   English only — other languages stripped for simplicity.
   The t() function and useTranslation() hook remain for consistency.
   ================================================================ */

export type Language = "en";

export interface LanguageInfo {
  code: Language;
  name: string;
  nativeName: string;
  flag: string;
}

export const LANGUAGES: LanguageInfo[] = [
  { code: "en", name: "English", nativeName: "English", flag: "" },
];

type TranslationKey = keyof typeof translations.en;

const translations = {
  en: {
    // Welcome / Onboarding
    "welcome.title": "Einstein",
    "welcome.subtitle": "AI-powered second brain. Local-first markdown notes with automatic entity extraction, semantic search, and knowledge graphs.",
    "welcome.getStarted": "Get Started",
    "welcome.openExisting": "Open Existing Vault",
    "welcome.or": "or",

    // Onboarding steps
    "onboard.step1.title": "Choose Your Language",
    "onboard.step1.desc": "Select your preferred language for Einstein.",
    "onboard.step2.title": "Create Your Vault",
    "onboard.step2.desc": "Your vault is a folder where all your notes live as plain markdown files.",
    "onboard.step2.pathLabel": "Vault Path",
    "onboard.step2.pathPlaceholder": "e.g., ~/Documents/my-brain",
    "onboard.step2.pathHint": "Enter a folder path. It will be created if it doesn't exist.",
    "onboard.step2.vaultName": "Vault Name",
    "onboard.step2.vaultNamePlaceholder": "My Second Brain",
    "onboard.step3.title": "Set Your Preferences",
    "onboard.step3.desc": "Customize Einstein to your liking.",
    "onboard.step3.theme": "Theme",
    "onboard.step3.themeDark": "Dark",
    "onboard.step3.themeLight": "Light",
    "onboard.step3.themeWarm": "Warm Dark",
    "onboard.step3.aiMode": "AI Mode",
    "onboard.step3.aiLocal": "Local (Ollama)",
    "onboard.step3.aiCloud": "Cloud (OpenAI)",
    "onboard.step3.aiNone": "No AI",
    "onboard.step3.aiLocalDesc": "Free, private — runs on your machine",
    "onboard.step3.aiCloudDesc": "More powerful — requires API key",
    "onboard.step3.aiNoneDesc": "Plain note-taking, no AI features",
    "onboard.step4.title": "You're All Set!",
    "onboard.step4.desc": "Your AI-powered second brain is ready.",
    "onboard.step4.tip1": "Create notes with ⌘N",
    "onboard.step4.tip2": "Link notes with [[wikilinks]]",
    "onboard.step4.tip3": "Search everything with ⌘P",
    "onboard.step4.tip4": "Daily notes from the calendar icon",
    "onboard.step4.tip5": "AI extracts entities automatically",
    "onboard.step4.launch": "Start Using Einstein",

    "onboard.next": "Next",
    "onboard.back": "Back",
    "onboard.skip": "Skip",

    // Editor
    "editor.placeholder": "Start writing... Use [[wikilinks]] to connect ideas.",
    "editor.save": "Save",
    "editor.saving": "Saving...",
    "editor.saved": "Saved",
    "editor.extracting": "Extracting entities...",
    "editor.words": "words",
    "editor.emptyTitle": "Select a note or create a new one",
    "editor.emptyHint.search": "search",
    "editor.emptyHint.new": "new note",

    // Sidebar
    "sidebar.files": "Files",
    "sidebar.search": "Search",
    "sidebar.graph": "Graph",
    "sidebar.backlinks": "Backlinks",
    "sidebar.canvas": "Canvas",
    "sidebar.calendar": "Calendar",
    "sidebar.kanban": "Kanban",
    "sidebar.export": "Export/Import",
    "sidebar.plugins": "Plugins",
    "sidebar.bookmarks": "Bookmarks",
    "sidebar.settings": "Settings",
    "sidebar.newNote": "New note",
    "sidebar.dailyNote": "Daily note",

    // Right Panel
    "panel.outline": "Outline",
    "panel.properties": "Properties",
    "panel.path": "Path",
    "panel.words": "Words",
    "panel.updated": "Updated",
    "panel.entities": "AI Entities",
    "panel.outgoing": "Outgoing Links",
    "panel.backlinks": "Backlinks",
    "panel.unlinked": "Unlinked Mentions",
    "panel.noBacklinks": "No other notes link here",
    "panel.versions": "Version History",
    "panel.noNote": "No note selected",

    // Search
    "search.placeholder": "Search notes...",
    "search.noResults": "No results found",

    // Settings
    "settings.title": "Settings",
    "settings.mode": "Connection Mode",
    "settings.modeLocal": "Local Only",
    "settings.modeCloud": "Cloud",
    "settings.language": "Language",
    "settings.theme": "Theme",
    "settings.ai": "AI Sidecar",
    "settings.aiConnected": "Connected",
    "settings.aiDisconnected": "Not connected",
    "settings.voice": "Voice Input",
    "settings.voiceEnabled": "Enabled",
    "settings.voiceDisabled": "Disabled",

    // Voice
    "voice.listening": "Listening...",
    "voice.speak": "Speak now",
    "voice.stop": "Stop",
    "voice.unsupported": "Voice input is not supported in this browser.",

    // General
    "general.cancel": "Cancel",
    "general.confirm": "Confirm",
    "general.delete": "Delete",
    "general.close": "Close",
    "general.loading": "Loading...",
    "general.error": "Error",
    "general.success": "Success",
    "general.noteNamePrompt": "Note name:",
    "general.create": "Create",
  },
} as const;

// Current language state
let currentLanguage: Language = "en";
const listeners: Set<() => void> = new Set();

export function setLanguage(lang: Language) {
  currentLanguage = lang;
  // Persist to localStorage
  try { localStorage.setItem("einstein-lang", lang); } catch {}
  // Notify all listeners
  listeners.forEach((fn) => fn());
}

export function getLanguage(): Language {
  return currentLanguage;
}

export function initLanguage() {
  // English only — no detection needed
  currentLanguage = "en";
}

export function t(key: TranslationKey): string {
  const lang = translations[currentLanguage];
  return (lang as Record<string, string>)?.[key] ?? (translations.en as Record<string, string>)[key] ?? key;
}

export function onLanguageChange(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

// React hook
import { useState, useEffect } from "react";

export function useTranslation() {
  const [, setTick] = useState(0);
  useEffect(() => {
    return onLanguageChange(() => setTick((t) => t + 1));
  }, []);
  return { t, lang: currentLanguage, setLanguage };
}

// Voice recognition language codes
export const VOICE_LANG_MAP: Record<Language, string> = {
  en: "en-US",
};
