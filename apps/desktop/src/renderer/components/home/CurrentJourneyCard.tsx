import { ArrowRight, MapPin } from "lucide-react";

import { Button } from "../ui/Button";
import { Card } from "../ui/Surface";
import type { HomeJourneyViewModel } from "./homeViewModel";

type CurrentJourneyCardProps = {
  journey: NonNullable<HomeJourneyViewModel["journey"]>;
  onContinue: () => void;
  onOpenJourney: () => void;
};

export function CurrentJourneyCard({ journey, onContinue, onOpenJourney }: CurrentJourneyCardProps) {
  return (
    <Card as="article" className="homeCurrentJourney" aria-labelledby="home-current-journey-title">
      <span className="homeSectionLabel">当前旅程</span>
      <h2 id="home-current-journey-title" title={journey.gameName}>{journey.gameName}</h2>
      {journey.location ? (
        <p className="homeJourneyLocation" title={journey.location}>
          <MapPin aria-hidden="true" size={17} strokeWidth={1.65} />
          <span>{journey.location}</span>
        </p>
      ) : null}
      <p className="homeJourneySummary">{journey.summary}</p>
      {journey.time ? <time className="homeJourneyTime">{journey.time}</time> : null}
      <div className="homeJourneyActions">
        <Button variant="primary" onClick={onContinue}>继续陪伴</Button>
        <Button variant="quiet" onClick={onOpenJourney}>
          查看旅程
          <ArrowRight aria-hidden="true" size={16} strokeWidth={1.6} />
        </Button>
      </div>
    </Card>
  );
}
