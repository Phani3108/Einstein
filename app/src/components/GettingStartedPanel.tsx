import { useState, useEffect, useCallback } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import {
  Rocket,
  Server,
  Database,
  Brain,
  Cpu,
  Cloud,
  HardDrive,
  CheckCircle,
  XCircle,
  Circle,
  Copy,
  ExternalLink,
  RefreshCw,
  Loader,
  ChevronDown,
  ChevronRight,
  Plug,
  Zap,
  ArrowRight,
} from "lucide-react";

type ServiceStatus = "connected" | "disconnected" | "not_configured" | "checking" | "idle";

interface StepState {
  status: ServiceStatus;
  message: string;
}

type Persona = "local" | "cloud" | null;

function StatusDot({ status }: { status: ServiceStatus }) {
  if (status === "checking") return <Loader size={14} className="gs-spin" />;
  if (status === "connected") return <CheckCircle size={14} color="#22c55e" />;
  if (status === "disconnected") return <XCircle size={14} color="#ef4444" />;
  if (status === "not_configured") return <Circle size={14} color="#71717a" />;
  return <Circle size={14} color="#3f3f46" />;
}

function CopyBlock({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <div className="gs-code-block">
      <code>{text}</code>
      <button onClick={copy} className="gs-copy-btn" title="Copy">
        {copied ? <CheckCircle size={12} /> : <Copy size={12} />}
      </button>
    </div>
  );
}

export function GettingStartedPanel() {
  const { dispatch } = useApp();
  const [persona, setPersona] = useState<Persona>(null);
  const [services, setServices] = useState<Record<string, StepState>>({});
  const [checking, setChecking] = useState(false);
  const [ollamaModels, setOllamaModels] = useState<any[]>([]);
  const [initMsg, setInitMsg] = useState("");
  const [seedMsg, setSeedMsg] = useState("");
  const [llmTestResult, setLlmTestResult] = useState("");

  const checkAllServices = useCallback(async () => {
    setChecking(true);
    try {
      const data = await api.getSetupStatus();
      const svcMap: Record<string, StepState> = {};
      for (const s of data.services || []) {
        svcMap[s.service] = { status: s.status, message: s.message };
      }
      svcMap["frontend"] = { status: "connected", message: "Running" };
      setServices(svcMap);
      if (!persona) {
        setPersona(data.mode === "local" ? "local" : "cloud");
      }
    } catch {
      setServices({ frontend: { status: "connected", message: "Running" }, backend: { status: "disconnected", message: "Backend not reachable" } });
    }
    setChecking(false);
  }, [persona]);

  useEffect(() => { checkAllServices(); }, []);

  const handleInitDb = async () => {
    setInitMsg("Initializing...");
    try {
      const res = await api.initDatabase();
      setInitMsg(res.status === "ok" ? "Database initialized!" : `Error: ${res.message}`);
      checkAllServices();
    } catch (e: any) {
      setInitMsg(`Failed: ${e.message}`);
    }
  };

  const handleSeed = async () => {
    setSeedMsg("Seeding...");
    try {
      const res = await fetch(`${localStorage.getItem("einstein_server_url") || (window.location.hostname !== "localhost" ? "" : "http://localhost:8000")}/api/v1/dev/seed`, { method: "POST", headers: { "Content-Type": "application/json" } });
      const data = await res.json();
      setSeedMsg(data.status === "ok" ? "Sample data seeded!" : `Error: ${data.message}`);
    } catch (e: any) {
      setSeedMsg(`Failed: ${e.message}`);
    }
  };

  const handleTestLlm = async () => {
    setLlmTestResult("Testing...");
    try {
      const res = await api.testLLM();
      setLlmTestResult(res.status === "ok" ? `Success: ${res.response?.slice(0, 100)}` : `Error: ${res.message}`);
    } catch (e: any) {
      setLlmTestResult(`Failed: ${e.message}`);
    }
  };

  const loadOllamaModels = async () => {
    try {
      const res = await api.getOllamaModels();
      if (res.status === "ok") setOllamaModels(res.models || []);
    } catch {}
  };

  const svc = (name: string): StepState => services[name] || { status: "idle", message: "" };

  const completedCount = Object.values(services).filter(s => s.status === "connected").length;
  const totalSteps = persona === "local" ? 6 : 5;

  return (
    <div className="gs-panel">
      <div className="gs-header">
        <div className="gs-title-row">
          <Rocket size={24} />
          <h1>Getting Started with Einstein</h1>
        </div>
        <p className="gs-subtitle">Set up your personal intelligence engine in minutes</p>
        {persona && (
          <div className="gs-progress">
            <div className="gs-progress-bar">
              <div className="gs-progress-fill" style={{ width: `${Math.min(100, (completedCount / totalSteps) * 100)}%` }} />
            </div>
            <span className="gs-progress-text">{completedCount} of {totalSteps} services ready</span>
          </div>
        )}
      </div>

      {!persona ? (
        <div className="gs-persona-picker">
          <h2>Choose your setup mode</h2>
          <div className="gs-persona-cards">
            <button className="gs-persona-card" onClick={() => { setPersona("local"); loadOllamaModels(); }}>
              <HardDrive size={32} />
              <h3>Local Only</h3>
              <p>Run everything on your machine. No cloud services needed. Uses Ollama for AI and SQLite for storage.</p>
              <ul>
                <li>Free and private</li>
                <li>No API keys required</li>
                <li>Works offline</li>
              </ul>
            </button>
            <button className="gs-persona-card" onClick={() => setPersona("cloud")}>
              <Cloud size={32} />
              <h3>Cloud Connected</h3>
              <p>Use cloud AI services and managed databases for the best performance and integrations.</p>
              <ul>
                <li>Fastest AI models</li>
                <li>Managed infrastructure</li>
                <li>Full integrations</li>
              </ul>
            </button>
          </div>
        </div>
      ) : (
        <div className="gs-steps-container">
          <div className="gs-mode-toggle">
            <button className={persona === "local" ? "gs-mode-active" : ""} onClick={() => { setPersona("local"); loadOllamaModels(); }}>
              <HardDrive size={14} /> Local
            </button>
            <button className={persona === "cloud" ? "gs-mode-active" : ""} onClick={() => setPersona("cloud")}>
              <Cloud size={14} /> Cloud
            </button>
            <button className="gs-refresh-btn" onClick={checkAllServices} disabled={checking}>
              <RefreshCw size={14} className={checking ? "gs-spin" : ""} /> Refresh Status
            </button>
          </div>

          {persona === "local" && (
            <div className="gs-steps">
              <div className="gs-step">
                <div className="gs-step-header">
                  <StatusDot status={svc("database").status === "connected" ? "connected" : "idle"} />
                  <Database size={16} />
                  <h3>1. Install Python & Einstein</h3>
                </div>
                <div className="gs-step-body">
                  <p>Install Python 3.11+ and the Einstein backend:</p>
                  <CopyBlock text="pip install -e '.[local]'" />
                  <p className="gs-hint">This installs all dependencies including SQLite support.</p>
                </div>
              </div>

              <div className="gs-step">
                <div className="gs-step-header">
                  <StatusDot status={svc("llm").status} />
                  <Brain size={16} />
                  <h3>2. Install Ollama</h3>
                </div>
                <div className="gs-step-body">
                  <p>Download and install Ollama for local AI:</p>
                  <a href="https://ollama.com/download" target="_blank" rel="noreferrer" className="gs-link">
                    <ExternalLink size={12} /> Download Ollama
                  </a>
                  <p style={{ marginTop: 8 }}>Then pull a model:</p>
                  <CopyBlock text="ollama pull llama3.2" />
                  {ollamaModels.length > 0 && (
                    <div className="gs-models-list">
                      <p className="gs-hint">Installed models:</p>
                      {ollamaModels.map(m => (
                        <span key={m.name} className="gs-model-badge">{m.name}</span>
                      ))}
                    </div>
                  )}
                  <button className="gs-action-btn" onClick={() => { loadOllamaModels(); checkAllServices(); }}>
                    <RefreshCw size={12} /> Check Ollama
                  </button>
                  {svc("llm").message && <p className="gs-status-msg">{svc("llm").message}</p>}
                </div>
              </div>

              <div className="gs-step">
                <div className="gs-step-header">
                  <StatusDot status={svc("embeddings").status} />
                  <Cpu size={16} />
                  <h3>3. Pull Embedding Model</h3>
                </div>
                <div className="gs-step-body">
                  <p>Pull a text embedding model for semantic search:</p>
                  <CopyBlock text="ollama pull nomic-embed-text" />
                  <p className="gs-hint">Set <code>EMBEDDING_PROVIDER=ollama</code> in your .env file.</p>
                </div>
              </div>

              <div className="gs-step">
                <div className="gs-step-header">
                  <StatusDot status={svc("database").status} />
                  <Database size={16} />
                  <h3>4. Set Up Local Environment</h3>
                </div>
                <div className="gs-step-body">
                  <p>Create a <code>.env</code> file in the project root:</p>
                  <CopyBlock text={`DATABASE_URL=sqlite+aiosqlite:///einstein.db\nLLM_MODEL=ollama/llama3.2\nOLLAMA_BASE_URL=http://localhost:11434\nEMBEDDING_PROVIDER=ollama\nEMBEDDING_MODEL=nomic-embed-text`} />
                  <button className="gs-action-btn" onClick={handleInitDb}>
                    <Database size={12} /> Initialize Database
                  </button>
                  {initMsg && <p className="gs-status-msg">{initMsg}</p>}
                </div>
              </div>

              <div className="gs-step">
                <div className="gs-step-header">
                  <StatusDot status={svc("database").status === "connected" ? "connected" : "idle"} />
                  <Server size={16} />
                  <h3>5. Start Einstein</h3>
                </div>
                <div className="gs-step-body">
                  <p>Start the backend server:</p>
                  <CopyBlock text="uvicorn src.api.app:app --reload --port 8000" />
                  <p style={{ marginTop: 8 }}>Start the frontend (in another terminal):</p>
                  <CopyBlock text="cd app && npm install && npm run dev" />
                  <button className="gs-action-btn" onClick={checkAllServices}>
                    <RefreshCw size={12} /> Check Connection
                  </button>
                </div>
              </div>

              <div className="gs-step">
                <div className="gs-step-header">
                  <StatusDot status={svc("llm").status} />
                  <Zap size={16} />
                  <h3>6. Verify & Load Data</h3>
                </div>
                <div className="gs-step-body">
                  <button className="gs-action-btn" onClick={handleTestLlm}>
                    <Brain size={12} /> Test AI Model
                  </button>
                  {llmTestResult && <p className="gs-status-msg">{llmTestResult}</p>}
                  <button className="gs-action-btn" onClick={handleSeed} style={{ marginTop: 8 }}>
                    <Database size={12} /> Load Sample Data
                  </button>
                  {seedMsg && <p className="gs-status-msg">{seedMsg}</p>}
                </div>
              </div>
            </div>
          )}

          {persona === "cloud" && (
            <div className="gs-steps">
              <div className="gs-step">
                <div className="gs-step-header">
                  <StatusDot status={svc("database").status} />
                  <Database size={16} />
                  <h3>1. Set Up PostgreSQL</h3>
                </div>
                <div className="gs-step-body">
                  <p>Create a managed PostgreSQL database:</p>
                  <div className="gs-provider-links">
                    <a href="https://neon.tech" target="_blank" rel="noreferrer" className="gs-link"><ExternalLink size={12} /> Neon</a>
                    <a href="https://supabase.com" target="_blank" rel="noreferrer" className="gs-link"><ExternalLink size={12} /> Supabase</a>
                    <a href="https://render.com" target="_blank" rel="noreferrer" className="gs-link"><ExternalLink size={12} /> Render</a>
                  </div>
                  <p style={{ marginTop: 8 }}>Set in <code>.env</code>:</p>
                  <CopyBlock text="DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname" />
                  <button className="gs-action-btn" onClick={checkAllServices}>
                    <RefreshCw size={12} /> Check Database
                  </button>
                  {svc("database").message && <p className="gs-status-msg">{svc("database").message}</p>}
                </div>
              </div>

              <div className="gs-step">
                <div className="gs-step-header">
                  <StatusDot status={svc("llm").status} />
                  <Brain size={16} />
                  <h3>2. Set Up AI Provider</h3>
                </div>
                <div className="gs-step-body">
                  <p>Get an API key from your preferred provider:</p>
                  <div className="gs-provider-links">
                    <a href="https://platform.openai.com/api-keys" target="_blank" rel="noreferrer" className="gs-link"><ExternalLink size={12} /> OpenAI</a>
                    <a href="https://console.anthropic.com" target="_blank" rel="noreferrer" className="gs-link"><ExternalLink size={12} /> Anthropic</a>
                    <a href="https://platform.deepseek.com" target="_blank" rel="noreferrer" className="gs-link"><ExternalLink size={12} /> DeepSeek</a>
                  </div>
                  <CopyBlock text={`OPENAI_API_KEY=sk-...\nLLM_MODEL=gpt-4`} />
                  <button className="gs-action-btn" onClick={handleTestLlm}>
                    <Brain size={12} /> Test AI Connection
                  </button>
                  {llmTestResult && <p className="gs-status-msg">{llmTestResult}</p>}
                </div>
              </div>

              <div className="gs-step">
                <div className="gs-step-header">
                  <StatusDot status={svc("vector_db").status} />
                  <Cpu size={16} />
                  <h3>3. Vector Database (Optional)</h3>
                </div>
                <div className="gs-step-body">
                  <p>For semantic search, set up Pinecone:</p>
                  <a href="https://www.pinecone.io" target="_blank" rel="noreferrer" className="gs-link"><ExternalLink size={12} /> Pinecone</a>
                  <CopyBlock text="PINECONE_API_KEY=your-key" />
                  <p className="gs-hint">Optional — Einstein works without it using keyword search.</p>
                </div>
              </div>

              <div className="gs-step">
                <div className="gs-step-header">
                  <StatusDot status={svc("redis").status} />
                  <Server size={16} />
                  <h3>4. Redis (Optional)</h3>
                </div>
                <div className="gs-step-body">
                  <p>For background intelligence workers:</p>
                  <a href="https://upstash.com" target="_blank" rel="noreferrer" className="gs-link"><ExternalLink size={12} /> Upstash Redis</a>
                  <CopyBlock text="REDIS_URL=redis://..." />
                  <p className="gs-hint">Optional — needed only for scheduled intelligence tasks.</p>
                </div>
              </div>

              <div className="gs-step">
                <div className="gs-step-header">
                  <StatusDot status={svc("database").status === "connected" ? "connected" : "idle"} />
                  <Plug size={16} />
                  <h3>5. Initialize & Connect</h3>
                </div>
                <div className="gs-step-body">
                  <button className="gs-action-btn" onClick={handleInitDb}>
                    <Database size={12} /> Initialize Database
                  </button>
                  {initMsg && <p className="gs-status-msg">{initMsg}</p>}
                  <button className="gs-action-btn" onClick={handleSeed} style={{ marginTop: 8 }}>
                    <Database size={12} /> Load Sample Data
                  </button>
                  {seedMsg && <p className="gs-status-msg">{seedMsg}</p>}
                  <button className="gs-action-btn" onClick={() => dispatch({ type: "SET_SIDEBAR_VIEW", view: "integrations" })} style={{ marginTop: 8 }}>
                    <Plug size={12} /> Connect Integrations
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="gs-footer">
            <button className="gs-skip-btn" onClick={() => dispatch({ type: "SET_SIDEBAR_VIEW", view: "contexthub" })}>
              Skip to Dashboard <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
