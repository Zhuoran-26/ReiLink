import { Swords } from "lucide-react";

import { JourneyCard } from "./JourneyCard";

type CurrentChallengeProps = {
  activity: string;
  name: string | null;
};

export function CurrentChallenge({ activity, name }: CurrentChallengeProps) {
  return (
    <JourneyCard className="currentChallenge" label="正在面对">
      <div className="journeySectionLabel">
        <Swords aria-hidden="true" size={15} strokeWidth={1.65} />
        <span>正在面对</span>
      </div>
      <h3>{name ?? "还没有明确的挑战"}</h3>
      <span className="journeyActivity">
        <i aria-hidden="true" />
        {activity || "旅程进行中"}
      </span>
    </JourneyCard>
  );
}
