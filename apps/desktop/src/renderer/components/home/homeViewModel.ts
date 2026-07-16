import type {
  GameContextResponse,
  GameSessionDebugResponse,
  GameStatus,
  SessionArchiveSummary
} from "../../../shared/api";
import { sanitizeSessionTimelineText, type SessionTimelineItem } from "../../sessionTimeline";

const EMPTY_VALUES = new Set(["idle", "none", "null", "undefined", "unknown", "无"]);

const displayText = (value: unknown, maxLength = 96) => {
  const text = sanitizeSessionTimelineText(value, maxLength);
  return text && !EMPTY_VALUES.has(text.toLowerCase()) ? text : null;
};

const sameGame = (left: string | null, right: string | null) =>
  Boolean(left && right && left.trim().toLocaleLowerCase() === right.trim().toLocaleLowerCase());

const timestampValue = (value: string | null | undefined) => {
  if (!value) return Number.NEGATIVE_INFINITY;
  const timestamp = new Date(value).getTime();
  return Number.isFinite(timestamp) ? timestamp : Number.NEGATIVE_INFINITY;
};

const latestJourneyArchive = (archives: SessionArchiveSummary[], gameName: string | null) => {
  let latest: SessionArchiveSummary | null = null;
  for (const archive of archives) {
    if (archive.is_deleted || (gameName && !sameGame(displayText(archive.game, 80), gameName))) continue;
    if (!latest || timestampValue(archive.ended_at) > timestampValue(latest.ended_at)) latest = archive;
  }
  return latest;
};

export const homeJourneyTime = (timestamp: string | null | undefined, now = new Date()) => {
  if (!timestamp) return null;
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return null;

  const day = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const daysAgo = Math.round((today - day) / 86_400_000);
  if (daysAgo === 0) return "今天";
  if (daysAgo === 1) return "昨天";
  if (daysAgo > 1 && daysAgo < 7) return `${daysAgo} 天前`;
  return date.toLocaleDateString("zh-CN", { month: "long", day: "numeric" });
};

const stripPrefix = (value: string, prefix: string) => value.startsWith(prefix) ? value.slice(prefix.length).trim() : value;

export const homeTimelineFragment = (item: SessionTimelineItem) => {
  switch (item.type) {
    case "game_selected": {
      const game = stripPrefix(item.summary, "切换游戏：");
      return game ? `${game} 的旅程重新翻开了一页。` : "一段旅程重新翻开了一页。";
    }
    case "boss_detected": {
      const challenge = stripPrefix(item.summary, "检测到 Boss：");
      return challenge ? `旅程停在了${challenge}面前。` : "前方出现了新的挑战。";
    }
    case "death_count_changed":
      return "你又重新出发了一次。";
    case "frustration_changed":
      return item.summary.includes("缓和") ? "这一段旅程慢慢平静下来。" : "这一段路走得有些起伏。";
    case "boss_cleared": {
      const challenge = stripPrefix(item.summary, "击败 Boss：");
      return challenge ? `你已经越过了${challenge}。` : "你已经越过了这次挑战。";
    }
    case "knowledge_used":
      return "你翻到了一页与旅程有关的参考。";
    case "proactive_shown":
      return "Rei 在这一段旅程里留过一句话。";
    case "memory_accepted":
      return "一段片段被收进了回忆。";
    case "memory_ignored":
      return "这段片段没有被留下。";
    case "memory_undone":
      return "一段记录从回忆里移开了。";
    default:
      return displayText(item.summary, 148);
  }
};

const archiveFragment = (archive: SessionArchiveSummary | null) => {
  if (!archive) return null;
  const safeSummary = displayText(archive.safe_event_summaries[archive.safe_event_summaries.length - 1], 148)
    ?? displayText(archive.summary, 148);
  if (!safeSummary) return null;

  const deathMatch = safeSummary.match(/(?:死亡次数更新|重新尝试)[：:]?\s*(\d+)?/i);
  if (deathMatch) return deathMatch[1] ? `你记录了第 ${deathMatch[1]} 次重新出发。` : "你又重新出发了一次。";
  const bossMatch = safeSummary.match(/(?:Boss|正在面对)[：:]?\s*(.+)/i);
  if (bossMatch?.[1]) return `你曾在这里面对${bossMatch[1].trim()}。`;
  const gameMatch = safeSummary.match(/游戏[：:]?\s*(.+)/i);
  if (gameMatch?.[1]) return `${gameMatch[1].trim()} 的一页已经被保存。`;
  return safeSummary;
};

export type HomeJourneyViewModel = {
  fragment: {
    text: string;
    time: string | null;
  } | null;
  journey: {
    challenge: string | null;
    gameName: string;
    location: string | null;
    summary: string;
    time: string | null;
  } | null;
  presence: {
    detail: string;
    supportingDetail: string | null;
    title: string;
  };
};

type BuildHomeJourneyViewModelInput = {
  archives: SessionArchiveSummary[];
  gameContext: GameContextResponse;
  gameSession: GameSessionDebugResponse;
  gameStatus: GameStatus;
  now?: Date;
  timeline: SessionTimelineItem[];
};

export function buildHomeJourneyViewModel({
  archives,
  gameContext,
  gameSession,
  gameStatus,
  now = new Date(),
  timeline
}: BuildHomeJourneyViewModelInput): HomeJourneyViewModel {
  const gameName = displayText(
    gameContext.active_game_display_name ?? gameSession.current_game ?? gameStatus.game_name,
    100
  );
  const archive = latestJourneyArchive(archives, gameName);
  const location = gameName ? displayText(archive?.area, 110) : null;
  const challenge = gameName
    ? displayText(gameSession.current_boss?.name ?? gameSession.discussion_target?.name ?? gameSession.last_attempted_boss, 110)
    : null;
  const latestTimeline = timeline[timeline.length - 1] ?? null;
  const recentTimestamp = latestTimeline?.timestamp ?? archive?.ended_at ?? gameSession.last_updated_at;
  const time = homeJourneyTime(recentTimestamp, now);

  if (!gameName) {
    return {
      journey: null,
      fragment: null,
      presence: {
        title: "欢迎回来。",
        detail: "这里还很安静。",
        supportingDetail: "等你准备好，我们可以从一段新的旅程开始。"
      }
    };
  }

  const summary = challenge
    ? `你还在面对${challenge}。`
    : location
      ? `上次，你准备继续在${location}探索。`
      : "这一段旅程还在继续。";
  const fragmentText = latestTimeline ? homeTimelineFragment(latestTimeline) : archiveFragment(archive);

  return {
    journey: {
      challenge,
      gameName,
      location,
      summary,
      time
    },
    fragment: fragmentText
      ? {
          text: sanitizeSessionTimelineText(fragmentText, 148),
          time
        }
      : null,
    presence: {
      title: "欢迎回来。",
      detail: location ? `我们上次停在${location}。` : `${gameName} 的旅程还在继续。`,
      supportingDetail: null
    }
  };
}
