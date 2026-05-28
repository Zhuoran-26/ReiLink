import { ChevronDown, ChevronUp, Mic, RefreshCw, Send } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { api, ChatDebugResponse, GameSessionDebugResponse, GameStatus, MemoryDebugResponse, UserProfileMemory } from "../shared/api";

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

const gameStatusText = {
  running: "运行中",
  idle: "空闲"
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

export const INTERIM_PLACEHOLDERS = ["……", "……嗯", "嗯……"];
const PLACEHOLDER_DELAY_MS = 3000;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const nextSegmentDelay = () => 500 + Math.floor(Math.random() * 401);

const pickPlaceholder = () => INTERIM_PLACEHOLDERS[Math.floor(Math.random() * INTERIM_PLACEHOLDERS.length)];

export function App() {
  const [backendStatus, setBackendStatus] = useState<"checking" | "connected" | "disconnected">("checking");
  const [gameStatus, setGameStatus] = useState<GameStatus>(idleStatus);
  const [memoryProfile, setMemoryProfile] = useState<UserProfileMemory>(emptyProfile);
  const [memoryDebug, setMemoryDebug] = useState<MemoryDebugResponse>(emptyMemoryDebug);
  const [chatDebug, setChatDebug] = useState<ChatDebugResponse>(emptyChatDebug);
  const [gameSessionDebug, setGameSessionDebug] = useState<GameSessionDebugResponse>(emptyGameSessionDebug);
  const [messages, setMessages] = useState<Message[]>([
    { id: "hello", role: "assistant", text: "我在。想问的时候就说。" }
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [debugOpen, setDebugOpen] = useState(false);
  const [lastError, setLastError] = useState("");
  const [lastInterimPlaceholderShown, setLastInterimPlaceholderShown] = useState(false);
  const [lastResponseLatencyMs, setLastResponseLatencyMs] = useState(0);

  const refreshStatus = async () => {
    try {
      setLastError("");
      await api.health();
      setBackendStatus("connected");
      setGameStatus(await api.gameStatus());
      setMemoryProfile(await api.memoryProfile());
      setMemoryDebug(await api.memoryDebug());
      setChatDebug(await api.chatDebug());
      setGameSessionDebug(await api.gameSessionDebug());
    } catch (error) {
      setBackendStatus("disconnected");
      setLastError(error instanceof Error ? error.message : "后端暂时连不上");
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

  const statusLabel = useMemo(() => {
    if (backendStatus === "checking") return "检查中";
    return backendStatus === "connected" ? "已连接" : "未连接";
  }, [backendStatus]);

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <h1>ReiLink</h1>
          <p>艾尔登法环中文陪伴助手</p>
        </div>
        <span className={`connection ${backendStatus}`}>{statusLabel}</span>
      </header>

      <section className="layout">
        <aside className="sidebar" aria-label="状态面板">
          <section className="panel">
            <div className="panelTitle">
              <h2>游戏状态</h2>
              <button aria-label="刷新游戏状态" className="iconButton" onClick={refreshStatus}>
                <RefreshCw size={17} />
              </button>
            </div>
            <div className={`statusBadge ${gameStatus.status}`}>艾尔登法环：{gameStatusText[gameStatus.status]}</div>
            <dl className="facts">
              <div>
                <dt>进程</dt>
                <dd>{gameStatus.process_name ?? "无"}</dd>
              </div>
              <div>
                <dt>置信度</dt>
                <dd>{gameStatus.confidence.toFixed(1)}</dd>
              </div>
            </dl>
          </section>

          <section className="panel characterPanel">
            <div className="avatar" aria-hidden="true">
              R
            </div>
            <h2>Rei</h2>
            <p>安静 / 冷淡</p>
          </section>

          <section className="panel">
            <button className="debugToggle" onClick={() => setDebugOpen((open) => !open)}>
              <span>调试</span>
              {debugOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
            {debugOpen && (
              <pre className="debugPanel">
                {JSON.stringify(
                  {
                    gameStatus,
                    personaId: "rei_like",
                    provider: "由后端配置",
                    memory: {
                      written: memoryDebug.memory_written,
                      current_boss: memoryProfile.current_boss,
                      repeated_struggles: memoryProfile.repeated_struggles,
                      preferred_tone: memoryProfile.preferred_tone,
                      emotional_note: memoryDebug.emotional_note ?? memoryProfile.emotional_notes.at(-1) ?? null,
                      recent_episode_count: memoryDebug.recent_episode_count
                    },
                    memory_provenance: memoryDebug.items,
                    game_session: {
                      current_game: gameSessionDebug.current_game,
                      current_boss: gameSessionDebug.current_boss?.name ?? null,
                      current_boss_confidence: gameSessionDebug.current_boss?.confidence ?? null,
                      current_boss_age_hours: gameSessionDebug.current_boss?.age_hours ?? null,
                      current_boss_is_fresh: gameSessionDebug.current_boss?.is_fresh ?? false,
                      last_boss: gameSessionDebug.last_boss,
                      last_attempted_boss: gameSessionDebug.last_attempted_boss,
                      last_cleared_boss: gameSessionDebug.last_cleared_boss,
                      boss_history: gameSessionDebug.boss_history,
                      death_count: gameSessionDebug.death_count,
                      frustration_count: gameSessionDebug.frustration_count,
                      last_game_intent: gameSessionDebug.last_game_intent
                    },
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
            )}
          </section>
        </aside>

        <section className="chatPanel" aria-label="聊天面板">
          <div className="messages">
            {messages.map((message) => (
              <article className={`message ${message.role}`} key={message.id}>
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
    </main>
  );
}
