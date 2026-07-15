import { ReiAvatar } from "../rei/ReiAvatar";
import { CurrentChallenge } from "./CurrentChallenge";
import { EmptyJourney } from "./EmptyJourney";
import { JourneyTrail } from "./JourneyTrail";

export type JourneyHistoryEntry = {
  name: string;
  status: string;
};

type JourneyOverviewProps = {
  activity: string;
  challengeName: string | null;
  gameName: string | null;
  history: JourneyHistoryEntry[];
  lastAttempted: string | null;
  lastCleared: string | null;
  retryCount: number;
};

const retrySummary = (retryCount: number) => {
  if (retryCount <= 0) return "还没有新的重新尝试";
  return `记录了 ${retryCount} 次重新尝试`;
};

export function JourneyOverview({
  activity,
  challengeName,
  gameName,
  history,
  lastAttempted,
  lastCleared,
  retryCount
}: JourneyOverviewProps) {
  if (!gameName) return <EmptyJourney />;

  return (
    <section aria-label="当前旅程" className="journeyPage journeyOverview">
      <JourneyTrail />
      <header className="journeyHero">
        <h2>{gameName}</h2>
        <p>这一段旅程仍在继续。</p>
        <div className="journeyReiNote">
          <ReiAvatar name="Rei" size="small" state="idle" />
          <span>Rei 会记下重要片段。</span>
        </div>
      </header>

      <CurrentChallenge activity={activity} name={challengeName} />

      <section aria-label="最近脚步" className="journeyFootsteps">
        <div className="journeyRuledHeading">
          <h3>最近脚步</h3>
        </div>
        <dl>
          <div>
            <dt>最近挑战</dt>
            <dd>{lastAttempted ?? "还没有记录"}</dd>
          </div>
          <div>
            <dt>已越过</dt>
            <dd>{lastCleared ?? "还没有记录"}</dd>
          </div>
          <div>
            <dt>本局记录</dt>
            <dd>{retrySummary(retryCount)}</dd>
          </div>
        </dl>
      </section>

      {history.length > 0 ? (
        <ol aria-label="最近挑战记录" className="journeyHistory">
          {history.map((entry, index) => (
            <li key={`${entry.name}-${entry.status}-${index}`}>
              <strong>{entry.name}</strong>
              <span>{entry.status}</span>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}
