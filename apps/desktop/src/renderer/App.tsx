import {
  Bot,
  Brain,
  Bug,
  ChevronDown,
  ChevronUp,
  Database,
  Gamepad2,
  MessageSquare,
  Mic,
  RefreshCw,
  Send,
  Settings,
  Sparkles
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  api,
  AppSettings,
  ChatDebugResponse,
  GameSessionDebugResponse,
  GameStatus,
  MemoryDebugResponse,
  PendingMemory,
  PromptPreviewResponse,
  SemanticExtractionDebugResponse,
  UserProfileMemory
} from "../shared/api";

type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  pending?: boolean;
};

const idleStatus: GameStatus = {
  game_id: null,
  game_name: null,
  process_name: null,
  status: "idle",
  confidence: 0,
  tags: []
};

const emptyProfile: UserProfileMemory = {
  user_name: null,
  favorite_game: null,
  preferred_tone: null,
  likes_teasing: null,
  skill_level: null,
  current_boss: null,
  repeated_struggles: [],
  emotional_notes: [],
  last_seen_at: null,
  memory_updated_at: {}
};

const emptyMemoryDebug: MemoryDebugResponse = {
  prompt_order: [],
  memory_written: false,
  current_boss: null,
  emotional_note: null,
  recent_episode_count: 0,
  items: []
};

const emptyChatDebug: ChatDebugResponse = {
  intent: null,
  selected_model: null,
  thinking_enabled: false,
  reasoning_effort: null,
  prompt_tokens_estimate: 0,
  llm_latency_ms: 0,
  memory_latency_ms: 0,
  total_latency_ms: 0,
  reply_segments_count: 0,
  segmenter_mode: null
};

const emptyGameSessionDebug: GameSessionDebugResponse = {
  current_game: null,
  current_boss: null,
  last_boss: null,
  last_attempted_boss: null,
  last_cleared_boss: null,
  current_activity: null,
  recent_game_topics: [],
  boss_history: [],
  frustration_count: 0,
  death_count: 0,
  last_user_intent: null,
  last_game_intent: null,
  last_updated_at: null
};

const emptyPromptPreview: PromptPreviewResponse = {
  persona_mode: "unknown",
  current_user_message: null,
  prompt_order: [],
  session_focus_summary: {},
  game_state_summary: {},
  memory_summary: {},
  final_context_summary: {},
  warnings: []
};

const emptySemanticExtractionDebug: SemanticExtractionDebugResponse = {
  latest_user_message: null,
  rule_result: null,
  rule_confidence: 0,
  llm_called: false,
  llm_result: null,
  final_decision: null,
  skip_reason: null,
  latency_ms: 0,
  parse_error: null
};

const defaultAppSettings: AppSettings = {
  persona_mode: "guarded",
  debug_panel: "show",
  memory_enabled: true,
  pending_memory_mode: "manual",
  response_length: "normal",
  model_preference: "auto"
};

export const INTERIM_PLACEHOLDERS = ["……", "……嗯", "嗯……"];
const PLACEHOLDER_DELAY_MS = 3000;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const nextSegmentDelay = () => 500 + Math.floor(Math.random() * 401);

const pickPlaceholder = () => INTERIM_PLACEHOLDERS[Math.floor(Math.random() * INTERIM_PLACEHOLDERS.length)];

const asRecord = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};

const asArray = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);

const debugText = (value: unknown, fallback = "无") => {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
};

const bossName = (value: unknown) => {
  const boss = asRecord(value);
  return debugText(boss.name ?? value);
};

const debugListText = (item: unknown) => {
  const record = asRecord(item);
  const source = debugText(record.source, "");
  const field = debugText(record.field, "");
  const reason = debugText(record.reason, "");
  const text = debugText(record.text ?? record.summary ?? record.name ?? item);
  const meta = [source, field, reason].filter(Boolean).join(" / ");
  return meta ? `${meta}: ${text}` : text;
};

const pendingEvidenceSummary = (memory: PendingMemory) => {
  const evidence = asRecord(memory.evidence);
  const userMessage = debugText(evidence.user_message, "");
  const gameState = debugText(evidence.game_state_summary, "");
  const parts = [
    userMessage ? `user: ${userMessage}` : "",
    gameState ? `game: ${gameState}` : ""
  ].filter(Boolean);
  return parts.join(" / ") || "无";
};

const firstDefined = (...values: unknown[]) => values.find((value) => value !== null && value !== undefined && value !== "");

function BooleanBadge({ value }: { value: boolean }) {
  return <span className={`boolBadge ${value ? "true" : "false"}`}>{value ? "true" : "false"}</span>;
}

export function App() {
  const [backendStatus, setBackendStatus] = useState<"checking" | "connected" | "disconnected">("checking");
  const [gameStatus, setGameStatus] = useState<GameStatus>(idleStatus);
  const [memoryProfile, setMemoryProfile] = useState<UserProfileMemory>(emptyProfile);
  const [memoryDebug, setMemoryDebug] = useState<MemoryDebugResponse>(emptyMemoryDebug);
  const [chatDebug, setChatDebug] = useState<ChatDebugResponse>(emptyChatDebug);
  const [gameSessionDebug, setGameSessionDebug] = useState<GameSessionDebugResponse>(emptyGameSessionDebug);
  const [semanticDebug, setSemanticDebug] = useState<SemanticExtractionDebugResponse>(emptySemanticExtractionDebug);
  const [promptPreview, setPromptPreview] = useState<PromptPreviewResponse>(emptyPromptPreview);
  const [pendingMemories, setPendingMemories] = useState<PendingMemory[]>([]);
  const [pendingMemoryBusyId, setPendingMemoryBusyId] = useState("");
  const [debugActionBusy, setDebugActionBusy] = useState("");
  const [appSettings, setAppSettings] = useState<AppSettings>(defaultAppSettings);
  const [settingsBusy, setSettingsBusy] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    { id: "hello", role: "assistant", text: "我在。想问的时候就说。" }
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [debugOpen, setDebugOpen] = useState(false);
  const [promptPreviewOpen, setPromptPreviewOpen] = useState(false);
  const [lastError, setLastError] = useState("");
  const [lastInterimPlaceholderShown, setLastInterimPlaceholderShown] = useState(false);
  const [lastResponseLatencyMs, setLastResponseLatencyMs] = useState(0);

  const refreshStatus = async () => {
    try {
      setLastError("");
      await api.health();
      setBackendStatus("connected");
      setAppSettings(await api.settings());
      setGameStatus(await api.gameStatus());
      setMemoryProfile(await api.memoryProfile());
      setMemoryDebug(await api.memoryDebug());
      setChatDebug(await api.chatDebug());
      setGameSessionDebug(await api.gameSessionDebug());
      setSemanticDebug(await api.semanticExtractionDebug());
      setPromptPreview(await api.promptPreview());
      setPendingMemories(await api.pendingMemories());
    } catch (error) {
      setBackendStatus("disconnected");
      setLastError(error instanceof Error ? error.message : "后端暂时连不上");
    }
  };

  const updateAppSettings = async (patch: Partial<AppSettings>) => {
    const busyKey = Object.keys(patch)[0] ?? "settings";
    setSettingsBusy(busyKey);
    try {
      setLastError("");
      const updated = await api.updateSettings(patch);
      setAppSettings(updated);
      if (patch.debug_panel === "hide") {
        setDebugOpen(false);
        setPromptPreviewOpen(false);
      }
      await refreshStatus();
    } catch (error) {
      setLastError(error instanceof Error ? error.message : "settings update failed");
    } finally {
      setSettingsBusy("");
    }
  };

  useEffect(() => {
    void refreshStatus();
  }, []);

  const sendMessage = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending) return;
    const userMessage: Message = { id: crypto.randomUUID(), role: "user", text: trimmed };
    const placeholderId = crypto.randomUUID();
    let placeholderShown = false;
    const requestStartedAt = Date.now();
    setLastInterimPlaceholderShown(false);
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setSending(true);
    const placeholderTimer = window.setTimeout(() => {
      placeholderShown = true;
      setLastInterimPlaceholderShown(true);
      setMessages((current) => [
        ...current,
        { id: placeholderId, role: "assistant", text: pickPlaceholder(), pending: true }
      ]);
    }, PLACEHOLDER_DELAY_MS);
    try {
      const response = await api.chat(trimmed);
      window.clearTimeout(placeholderTimer);
      setLastResponseLatencyMs(Date.now() - requestStartedAt);
      setMessages((current) => current.filter((message) => message.id !== placeholderId));
      const segments = response.reply_segments.length > 0 ? response.reply_segments : [response.reply];
      for (const [index, segment] of segments.entries()) {
        if (index > 0) {
          await sleep(nextSegmentDelay());
        }
        setMessages((current) => [
          ...current,
          { id: crypto.randomUUID(), role: "assistant", text: segment, pending: false }
        ]);
      }
      setLastInterimPlaceholderShown(placeholderShown);
      await refreshStatus();
    } catch (error) {
      window.clearTimeout(placeholderTimer);
      setLastResponseLatencyMs(Date.now() - requestStartedAt);
      const errorMessage = error instanceof Error ? error.message : "发送失败";
      setLastError(errorMessage);
      const reply = /timeout|timed out|504|太慢/i.test(errorMessage)
        ? "线路太慢了。等一下再试。"
        : "线路有点安静。先检查后端。";
      setMessages((current) => [
        ...current.filter((message) => message.id !== placeholderId),
        { id: crypto.randomUUID(), role: "assistant", text: reply, pending: false }
      ]);
      setLastInterimPlaceholderShown(placeholderShown);
    } finally {
      setSending(false);
    }
  };

  const handlePendingMemory = async (id: string, action: "accept" | "ignore") => {
    setPendingMemoryBusyId(id);
    try {
      if (action === "accept") {
        await api.acceptPendingMemory(id);
      } else {
        await api.ignorePendingMemory(id);
      }
      await refreshStatus();
    } catch (error) {
      setLastError(error instanceof Error ? error.message : "pending memory update failed");
    } finally {
      setPendingMemoryBusyId("");
    }
  };

  const handleDebugAction = async (
    action: "refresh" | "reset-game-session" | "reset-memory" | "clear-pending"
  ) => {
    setDebugActionBusy(action);
    try {
      setLastError("");
      if (action === "reset-game-session") {
        await api.resetGameSession();
      } else if (action === "reset-memory") {
        await api.resetMemory();
      } else if (action === "clear-pending") {
        await api.clearPendingMemories();
      }
      await refreshStatus();
    } catch (error) {
      setLastError(error instanceof Error ? error.message : "debug action failed");
    } finally {
      setDebugActionBusy("");
    }
  };

  const statusLabel = useMemo(() => {
    if (backendStatus === "checking") return "检查中";
    return backendStatus === "connected" ? "已连接" : "未连接";
  }, [backendStatus]);

  const sessionFocusSummary = asRecord(promptPreview.session_focus_summary);
  const promptGameState = asRecord(promptPreview.game_state_summary);
  const promptBossHistory = asArray(promptGameState.boss_history);
  const gameStateSummary = {
    current_game: firstDefined(promptGameState.current_game, gameSessionDebug.current_game),
    current_boss: firstDefined(promptGameState.current_boss, gameSessionDebug.current_boss),
    current_activity: firstDefined(promptGameState.current_activity, gameSessionDebug.current_activity),
    freshness: firstDefined(promptGameState.freshness, gameSessionDebug.current_boss?.freshness),
    death_count: firstDefined(promptGameState.death_count, gameSessionDebug.death_count),
    frustration_count: firstDefined(promptGameState.frustration_count, gameSessionDebug.frustration_count),
    last_attempted_boss: firstDefined(promptGameState.last_attempted_boss, gameSessionDebug.last_attempted_boss),
    last_cleared_boss: firstDefined(promptGameState.last_cleared_boss, gameSessionDebug.last_cleared_boss),
    boss_history: promptBossHistory.length > 0 ? promptBossHistory : gameSessionDebug.boss_history
  };
  const memorySummary = asRecord(promptPreview.memory_summary);
  const injectedMemory = asArray(memorySummary.injected);
  const skippedMemory = asArray(memorySummary.skipped);
  const semanticRuleResult = asRecord(semanticDebug.rule_result);
  const semanticLlmResult = asRecord(semanticDebug.llm_result);
  const semanticLlmGameEvent = asRecord(semanticLlmResult.game_event);
  const semanticLlmMemoryCandidate = asRecord(semanticLlmResult.memory_candidate);
  const semanticFinalDecision = asRecord(semanticDebug.final_decision);
  const semanticFinalGameEvent = asRecord(semanticFinalDecision.game_event);
  const semanticFinalMemoryCandidate = asRecord(semanticFinalDecision.memory_candidate);
  const recentBossHistory = gameSessionDebug.boss_history.slice(0, 5);
  const debugPanelVisible = appSettings.debug_panel === "show";
  const displayGame = gameSessionDebug.current_game ?? gameStatus.game_name ?? "idle";
  const displayBoss = gameSessionDebug.current_boss?.name ?? null;
  const displayActivity = gameSessionDebug.current_activity ?? "idle";
  const companionName = "Rei";
  const companionSubtitle = "安静、冷淡的游戏陪伴";
  const companionStatus = backendStatus === "connected" ? "在线" : backendStatus === "checking" ? "检查中" : "离线";

  return (
    <main className="shell">
      <aside className="appSidebar" aria-label="应用导航">
        <div className="sidebarBrand">
          <Sparkles size={21} />
          <span>ReiLink</span>
        </div>

        <nav className="navMenu" aria-label="应用导航">
          <a className="navItem active" href="#chat-panel">
            <MessageSquare size={18} />
            <span>Chat</span>
          </a>
          <a className="navItem" href="#pending-memory-panel">
            <Database size={18} />
            <span>Memory</span>
          </a>
          <a className="navItem" href="#game-session-panel">
            <Gamepad2 size={18} />
            <span>Game</span>
          </a>
          <a className="navItem" href="#settings-panel">
            <Settings size={18} />
            <span>Settings</span>
          </a>
          <a className="navItem" href="#debug-panel">
            <Bug size={18} />
            <span>Debug</span>
          </a>
        </nav>

        <div className="companionStatusCard">
          <div className="miniAvatar" aria-hidden="true">
            {companionName.slice(0, 1)}
          </div>
          <div>
            <span>当前 Companion</span>
            <strong>{companionName}</strong>
            <p>
              <span className={`statusDot ${backendStatus}`} />
              {companionStatus}
            </p>
          </div>
        </div>
      </aside>

      <section className="appWorkspace">
        <header className="workspaceHeader">
          <div className="companionIntro">
            <div className="companionAvatar" aria-hidden="true">
              {companionName.slice(0, 1)}
            </div>
            <div>
              <p className="eyebrow">Companion</p>
              <h1>
                {companionName}
                <span className={`statusDot ${backendStatus}`} />
                <em>{companionStatus}</em>
              </h1>
              <p>{companionSubtitle}</p>
            </div>
          </div>
          <div className="statusStrip" aria-label="当前状态">
            <span className="topChip">
              <Brain size={15} />
              Persona: {appSettings.persona_mode}
            </span>
            <span className="topChip">
              <Bot size={15} />
              Model: {appSettings.model_preference}
            </span>
            <span className="topChip">
              <Gamepad2 size={15} />
              Game: {displayGame}
            </span>
            <span className="topChip">Boss: {displayBoss ?? "idle"}</span>
            <span className={`connection ${backendStatus}`}>{statusLabel}</span>
            <button aria-label="刷新状态" className="iconButton soft" onClick={refreshStatus}>
              <RefreshCw size={17} />
            </button>
          </div>
        </header>

        <section className="workspaceGrid">
          <section className="chatColumn" aria-label="主聊天界面" id="chat-panel">
            <div className="timelineMarker">今天</div>

          <section className="chatPanel" aria-label="聊天面板">
            <div className="messages">
              {messages.map((message) => (
                <article
                  className={`messageBubble ${message.role}${message.pending ? " pending" : ""}`}
                  key={message.id}
                >
                  <span>{message.role === "user" ? "你" : "Rei"}</span>
                  <p>{message.text}</p>
                </article>
              ))}
            </div>

            <form className="composer" onSubmit={sendMessage}>
              <button className="iconButton disabled" type="button" aria-label="按住说话实验功能" disabled>
                <Mic size={18} />
              </button>
              <input
                aria-label="聊天输入"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="问 Margit、路线、装备，或者随便说点什么。"
              />
              <button className="sendButton" type="submit" disabled={sending || !input.trim()}>
                <Send size={18} />
                <span>{sending ? "发送中" : "发送"}</span>
              </button>
            </form>
          </section>
        </section>

        <aside className="infoRail" aria-label="信息侧栏">
          <section className="infoCard settingsPanel" aria-label="Settings" id="settings-panel">
            <div className="cardHeader">
              <Settings size={17} />
              <h2>Settings</h2>
            </div>
            <div className="settingRows">
              <label className="settingRow">
                <span>Persona Mode</span>
                <select
                  aria-label="Persona Mode"
                  disabled={settingsBusy !== ""}
                  value={appSettings.persona_mode}
                  onChange={(event) =>
                    void updateAppSettings({ persona_mode: event.target.value as AppSettings["persona_mode"] })
                  }
                >
                  <option value="minimal">minimal</option>
                  <option value="guarded">guarded</option>
                </select>
              </label>
              <label className="settingRow">
                <span>Debug Panel</span>
                <select
                  aria-label="Debug Panel"
                  disabled={settingsBusy !== ""}
                  value={appSettings.debug_panel}
                  onChange={(event) =>
                    void updateAppSettings({ debug_panel: event.target.value as AppSettings["debug_panel"] })
                  }
                >
                  <option value="show">show</option>
                  <option value="hide">hide</option>
                </select>
              </label>
              <label className="settingRow">
                <span>Memory</span>
                <select
                  aria-label="Memory"
                  disabled={settingsBusy !== ""}
                  value={appSettings.memory_enabled ? "enabled" : "disabled"}
                  onChange={(event) => void updateAppSettings({ memory_enabled: event.target.value === "enabled" })}
                >
                  <option value="enabled">enabled</option>
                  <option value="disabled">disabled</option>
                </select>
              </label>
              <label className="settingRow">
                <span>Pending Memory Mode</span>
                <select aria-label="Pending Memory Mode" disabled value={appSettings.pending_memory_mode}>
                  <option value="manual">manual</option>
                </select>
              </label>
              <label className="settingRow">
                <span>Response Length</span>
                <select
                  aria-label="Response Length"
                  disabled={settingsBusy !== ""}
                  value={appSettings.response_length}
                  onChange={(event) =>
                    void updateAppSettings({ response_length: event.target.value as AppSettings["response_length"] })
                  }
                >
                  <option value="short">short</option>
                  <option value="normal">normal</option>
                </select>
              </label>
              <label className="settingRow">
                <span>Model Preference</span>
                <select
                  aria-label="Model Preference"
                  disabled={settingsBusy !== ""}
                  value={appSettings.model_preference}
                  onChange={(event) =>
                    void updateAppSettings({ model_preference: event.target.value as AppSettings["model_preference"] })
                  }
                >
                  <option value="auto">auto</option>
                  <option value="fast">fast</option>
                  <option value="pro">pro</option>
                </select>
              </label>
            </div>
            <p className="settingHint">本地保存到 settings.json，不包含密钥。</p>
          </section>

          <section className="infoCard pendingPanel" aria-label="Pending Memory" id="pending-memory-panel">
            <div className="cardHeader">
              <Database size={17} />
              <h2>Pending Memory</h2>
              <span className="countPill">{pendingMemories.length}</span>
            </div>
            <div className="pendingMemoryList">
              {pendingMemories.map((memory) => (
                <article className="pendingMemoryItem" key={memory.id}>
                  <p>{memory.text}</p>
                  <div className="pendingMemoryMeta">
                    <span>{memory.type}</span>
                    <span>{memory.source}</span>
                    <span>{memory.confidence.toFixed(2)}</span>
                  </div>
                  <p className="pendingMemoryEvidence">{pendingEvidenceSummary(memory)}</p>
                  <div className="pendingMemoryActions">
                    <button
                      className="smallButton"
                      type="button"
                      disabled={pendingMemoryBusyId === memory.id}
                      onClick={() => void handlePendingMemory(memory.id, "accept")}
                    >
                      Accept
                    </button>
                    <button
                      className="smallButton quiet"
                      type="button"
                      disabled={pendingMemoryBusyId === memory.id}
                      onClick={() => void handlePendingMemory(memory.id, "ignore")}
                    >
                      Ignore
                    </button>
                  </div>
                </article>
              ))}
              {pendingMemories.length === 0 && <p className="emptyDebugText">暂无待确认记忆</p>}
            </div>
          </section>

          <section className="infoCard gameSessionPanel" aria-label="Game Session" id="game-session-panel">
            <div className="cardHeader">
              <Gamepad2 size={17} />
              <h2>Game Session</h2>
            </div>
            <dl className="debugFacts">
              <div>
                <dt>current_game</dt>
                <dd>{debugText(gameSessionDebug.current_game)}</dd>
              </div>
              <div>
                <dt>current_boss</dt>
                <dd>{debugText(gameSessionDebug.current_boss?.name)}</dd>
              </div>
              <div>
                <dt>freshness</dt>
                <dd>{debugText(gameSessionDebug.current_boss?.freshness)}</dd>
              </div>
              <div>
                <dt>activity</dt>
                <dd>{debugText(gameSessionDebug.current_activity)}</dd>
              </div>
              <div>
                <dt>last_attempted</dt>
                <dd>{debugText(gameSessionDebug.last_attempted_boss)}</dd>
              </div>
              <div>
                <dt>last_cleared</dt>
                <dd>{debugText(gameSessionDebug.last_cleared_boss)}</dd>
              </div>
              <div>
                <dt>death_count</dt>
                <dd>{gameSessionDebug.death_count}</dd>
              </div>
              <div>
                <dt>frustration</dt>
                <dd>{gameSessionDebug.frustration_count}</dd>
              </div>
            </dl>
            <ul className="debugList compact" aria-label="Recent boss history">
              {recentBossHistory.map((boss, index) => (
                <li key={`${boss.name}-${boss.status}-${index}`}>
                  {boss.name} / {boss.status} / {boss.freshness}
                </li>
              ))}
              {recentBossHistory.length === 0 && <li>无</li>}
            </ul>
          </section>

          {debugPanelVisible && (
            <section className="infoCard foldPanel" aria-label="Debug Panel" id="debug-panel">
              <button
                className="foldHeader"
                aria-expanded={debugOpen}
                onClick={() => setDebugOpen((open) => !open)}
              >
                <span>Debug Panel</span>
                {debugOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
              {debugOpen && (
                <div className="debugPanel">
                  <section className="debugSection">
                    <h3>Debug Actions</h3>
                    <div className="debugActions">
                      <button
                        className="smallButton"
                        type="button"
                        disabled={debugActionBusy !== ""}
                        onClick={() => void handleDebugAction("refresh")}
                      >
                        Refresh Debug
                      </button>
                      <button
                        className="smallButton"
                        type="button"
                        disabled={debugActionBusy !== ""}
                        onClick={() => void handleDebugAction("reset-game-session")}
                      >
                        Reset Game Session
                      </button>
                      <button
                        className="smallButton"
                        type="button"
                        disabled={debugActionBusy !== ""}
                        onClick={() => void handleDebugAction("reset-memory")}
                      >
                        Reset Memory
                      </button>
                      <button
                        className="smallButton"
                        type="button"
                        disabled={debugActionBusy !== ""}
                        onClick={() => void handleDebugAction("clear-pending")}
                      >
                        Clear Pending Memory
                      </button>
                    </div>
                  </section>

                  <section className="debugSection">
                    <h3>Semantic Extraction</h3>
                    <dl className="debugFacts">
                      <div>
                        <dt>latest_user</dt>
                        <dd>{debugText(semanticDebug.latest_user_message)}</dd>
                      </div>
                      <div>
                        <dt>rule_result</dt>
                        <dd>
                          {debugText(semanticRuleResult.type ?? semanticRuleResult.event ?? semanticDebug.rule_result)}
                        </dd>
                      </div>
                      <div>
                        <dt>confidence</dt>
                        <dd>{Number(semanticDebug.rule_confidence ?? 0).toFixed(2)}</dd>
                      </div>
                      <div>
                        <dt>llm_called</dt>
                        <dd>
                          <BooleanBadge value={semanticDebug.llm_called} />
                        </dd>
                      </div>
                      <div>
                        <dt>llm_event</dt>
                        <dd>{debugText(semanticLlmGameEvent.type)}</dd>
                      </div>
                      <div>
                        <dt>llm_memory</dt>
                        <dd>{debugText(semanticLlmMemoryCandidate.type)}</dd>
                      </div>
                      <div>
                        <dt>final_event</dt>
                        <dd>{debugText(semanticFinalGameEvent.type)}</dd>
                      </div>
                      <div>
                        <dt>final_memory</dt>
                        <dd>{debugText(semanticFinalMemoryCandidate.type)}</dd>
                      </div>
                      <div>
                        <dt>skip_reason</dt>
                        <dd>{debugText(semanticDebug.skip_reason)}</dd>
                      </div>
                      <div>
                        <dt>parse_error</dt>
                        <dd className={semanticDebug.parse_error ? "debugError" : ""}>
                          {debugText(semanticDebug.parse_error)}
                        </dd>
                      </div>
                      <div>
                        <dt>latency_ms</dt>
                        <dd>{Number(semanticDebug.latency_ms ?? 0).toFixed(0)}</dd>
                      </div>
                    </dl>
                  </section>

                  <details className="rawJsonDetails">
                    <summary>Raw JSON</summary>
                    <pre className="debugJson">
                      {JSON.stringify(
                        {
                          game_session: gameSessionDebug,
                          semantic_extraction: semanticDebug,
                          memory_debug: memoryDebug,
                          memory_profile: memoryProfile,
                          pending_memory: pendingMemories,
                          prompt_preview: promptPreview,
                          settings: appSettings,
                          chat: {
                            intent: chatDebug.intent,
                            selected_model: chatDebug.selected_model,
                            last_latency_ms: chatDebug.total_latency_ms,
                            llm_latency_ms: chatDebug.llm_latency_ms,
                            memory_latency_ms: chatDebug.memory_latency_ms,
                            reasoning_enabled: chatDebug.thinking_enabled,
                            reasoning_effort: chatDebug.reasoning_effort,
                            reply_segments_count: chatDebug.reply_segments_count,
                            segmenter_mode: chatDebug.segmenter_mode,
                            last_interim_placeholder_shown: lastInterimPlaceholderShown,
                            last_response_latency_ms: lastResponseLatencyMs
                          },
                          lastError: lastError || null
                        },
                        null,
                        2
                      )}
                    </pre>
                  </details>
                </div>
              )}
            </section>
          )}

          {debugPanelVisible && (
            <section className="infoCard foldPanel" aria-label="Prompt Preview" id="prompt-preview-panel">
              <button
                className="foldHeader"
                aria-expanded={promptPreviewOpen}
                onClick={() => setPromptPreviewOpen((open) => !open)}
              >
                <span>Prompt Preview</span>
                {promptPreviewOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
              {promptPreviewOpen && (
                <div className="debugPanel">
                  <dl className="debugFacts">
                    <div>
                      <dt>persona_mode</dt>
                      <dd>{promptPreview.persona_mode}</dd>
                    </div>
                    <div>
                      <dt>current_user_message</dt>
                      <dd>{debugText(promptPreview.current_user_message)}</dd>
                    </div>
                    <div>
                      <dt>prompt_order</dt>
                      <dd>{promptPreview.prompt_order.join(" -> ") || "无"}</dd>
                    </div>
                    <div>
                      <dt>session_focus</dt>
                      <dd>{debugText(sessionFocusSummary.prompt_line ?? sessionFocusSummary.boss)}</dd>
                    </div>
                    <div>
                      <dt>game_state</dt>
                      <dd>
                        {debugText(gameStateSummary.current_game)} / {bossName(gameStateSummary.current_boss)} /{" "}
                        {debugText(gameStateSummary.current_activity)} / {debugText(gameStateSummary.freshness)}
                      </dd>
                    </div>
                    <div>
                      <dt>memory</dt>
                      <dd>
                        injected {injectedMemory.length} / skipped {skippedMemory.length}
                      </dd>
                    </div>
                  </dl>
                  <div className="debugSubgroup">
                    <h4>Memory injected</h4>
                    <ul className="debugList">
                      {injectedMemory.map((item, index) => (
                        <li key={`${debugListText(item)}-${index}`}>{debugListText(item)}</li>
                      ))}
                      {injectedMemory.length === 0 && <li>无</li>}
                    </ul>
                  </div>
                  <div className="debugSubgroup">
                    <h4>Memory skipped</h4>
                    <ul className="debugList">
                      {skippedMemory.map((item, index) => (
                        <li key={`${debugListText(item)}-${index}`}>{debugListText(item)}</li>
                      ))}
                      {skippedMemory.length === 0 && <li>无</li>}
                    </ul>
                  </div>
                  <div className="debugSubgroup">
                    <h4>Warnings</h4>
                    <ul className="debugList">
                      {promptPreview.warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                      {promptPreview.warnings.length === 0 && <li>无</li>}
                    </ul>
                  </div>
                </div>
              )}
            </section>
          )}
        </aside>
      </section>
      </section>
    </main>
  );
}
