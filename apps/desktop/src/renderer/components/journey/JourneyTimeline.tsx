import { ReiAvatar } from "../rei/ReiAvatar";
import { Button } from "../ui/Button";
import type { SessionTimelineItem } from "../../sessionTimeline";

type JourneyTimelineProps = {
  items: SessionTimelineItem[];
  onClear: () => void;
};

const stripPrefix = (value: string, prefix: string) => value.startsWith(prefix) ? value.slice(prefix.length) : value;

const timelineCopy = (item: SessionTimelineItem) => {
  switch (item.type) {
    case "game_selected":
      return { title: "开始记录", detail: stripPrefix(item.summary, "切换游戏：") };
    case "boss_detected":
      return { title: "正在面对", detail: stripPrefix(item.summary, "检测到 Boss：") };
    case "death_count_changed": {
      const count = stripPrefix(item.summary, "死亡次数更新：");
      return { title: "再次尝试", detail: count ? `本局第 ${count} 次重新出发` : "又向前走了一次" };
    }
    case "frustration_changed":
      return {
        title: item.summary.includes("缓和") ? "缓一缓" : "旅途起伏",
        detail: item.summary.includes("缓和") ? "状态缓和" : "这一段稍微难走了一些"
      };
    case "boss_cleared":
      return { title: "已经越过", detail: stripPrefix(item.summary, "击败 Boss：") };
    case "knowledge_used":
      return { title: "翻到一页参考", detail: stripPrefix(item.summary, "使用知识：") };
    case "proactive_shown":
      return { title: "Rei 留下一句话", detail: stripPrefix(item.summary, "主动陪伴已显示：") };
    case "memory_accepted":
      return { title: "收进回忆", detail: "一段片段被保存" };
    case "memory_ignored":
      return { title: "没有留下", detail: "这段片段没有被保存" };
    case "memory_undone":
      return { title: "从回忆移开", detail: "一段记录已撤销" };
    default:
      return { title: "旅程片段", detail: item.summary };
  }
};

const timelineTime = (timestamp: string) => {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "时间未知";
  return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false });
};

export function JourneyTimeline({ items, onClear }: JourneyTimelineProps) {
  return (
    <section aria-label="最近记录" className="journeyPage journeyTimeline">
      <header className="journeyTimelineHeader">
        <div>
          <h2>最近记录</h2>
          <p>只留下这一段旅程里的关键变化。</p>
        </div>
        <Button disabled={items.length === 0} size="small" variant="quiet" onClick={onClear}>
          清空本局记录
        </Button>
      </header>

      {items.length > 0 ? (
        <ol aria-label="旅程记录列表" className="journeyTimelineList">
          {items.map((item, index) => {
            const copy = timelineCopy(item);
            return (
              <li key={`${item.id}-${index}`}>
                <time dateTime={item.timestamp}>{timelineTime(item.timestamp)}</time>
                <div>
                  <strong>{copy.title}</strong>
                  <span>{copy.detail}</span>
                </div>
              </li>
            );
          })}
        </ol>
      ) : (
        <div className="journeyTimelineEmpty">
          <ReiAvatar name="Rei" size="small" state="idle" />
          <div>
            <strong>还没有新的记录。</strong>
            <span>重要的片段，会留在这里。</span>
          </div>
        </div>
      )}

      {items.length > 0 ? (
        <div className="journeyTimelineContinuation">
          <ReiAvatar name="Rei" size="small" state="idle" />
          <span>新的片段，会继续留在这里。</span>
        </div>
      ) : null}
    </section>
  );
}
