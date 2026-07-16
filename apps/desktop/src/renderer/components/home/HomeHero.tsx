import { MessageSquareText } from "lucide-react";

import { ReiAvatar } from "../rei/ReiAvatar";
import { Button } from "../ui/Button";
import type { HomeJourneyViewModel } from "./homeViewModel";

type HomeHeroProps = {
  hasJourney: boolean;
  onOpenChat: () => void;
  presence: HomeJourneyViewModel["presence"];
};

export function HomeHero({ hasJourney, onOpenChat, presence }: HomeHeroProps) {
  return (
    <section className={`homeHero${hasJourney ? "" : " homeHero-empty"}`} aria-labelledby="home-welcome-title">
      <div className="homePresenceAnchor">
        <ReiAvatar label="Rei 在这里" name="Rei" size="large" state="idle" />
      </div>
      <div className="homeHeroCopy">
        <h2 id="home-welcome-title">{presence.title}</h2>
        <p>{presence.detail}</p>
        {presence.supportingDetail ? <span>{presence.supportingDetail}</span> : null}
        {!hasJourney ? (
          <Button className="homeEmptyPrimaryAction" variant="primary" onClick={onOpenChat}>
            <MessageSquareText aria-hidden="true" size={16} strokeWidth={1.7} />
            与 Rei 说话
          </Button>
        ) : null}
      </div>
    </section>
  );
}
