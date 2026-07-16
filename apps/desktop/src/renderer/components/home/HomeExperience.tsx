import { CurrentJourneyCard } from "./CurrentJourneyCard";
import { HomeHero } from "./HomeHero";
import { HomeQuickActions } from "./HomeQuickActions";
import { RecentJourneyFragment } from "./RecentJourneyFragment";
import type { HomeJourneyViewModel } from "./homeViewModel";

type HomeExperienceProps = {
  model: HomeJourneyViewModel;
  onOpenChat: () => void;
  onOpenJourney: () => void;
  onOpenVoice: () => void;
};

export function HomeExperience({ model, onOpenChat, onOpenJourney, onOpenVoice }: HomeExperienceProps) {
  return (
    <section
      aria-label="首页"
      className={`homeExperience${model.journey ? "" : " homeExperience-empty"}`}
    >
      <HomeHero hasJourney={Boolean(model.journey)} onOpenChat={onOpenChat} presence={model.presence} />
      {model.journey ? (
        <CurrentJourneyCard journey={model.journey} onContinue={onOpenChat} onOpenJourney={onOpenJourney} />
      ) : null}
      <RecentJourneyFragment fragment={model.fragment} />
      <HomeQuickActions onOpenChat={onOpenChat} onOpenJourney={onOpenJourney} onOpenVoice={onOpenVoice} />
    </section>
  );
}
