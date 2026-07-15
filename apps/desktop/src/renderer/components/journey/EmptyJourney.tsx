import { ReiAvatar } from "../rei/ReiAvatar";
import { JourneyTrail } from "./JourneyTrail";

export function EmptyJourney() {
  return (
    <section aria-label="空白旅程" className="journeyPage emptyJourney">
      <JourneyTrail quiet />
      <div className="emptyJourneyContent">
        <ReiAvatar label="Rei" name="Rei" size="medium" state="idle" />
        <div>
          <h2>还没有开始一段旅程。</h2>
          <p>等新的脚步出现，这里会慢慢留下记录。</p>
        </div>
      </div>
    </section>
  );
}
