import type { HomeJourneyViewModel } from "./homeViewModel";

type RecentJourneyFragmentProps = {
  fragment: HomeJourneyViewModel["fragment"];
};

export function RecentJourneyFragment({ fragment }: RecentJourneyFragmentProps) {
  if (!fragment) {
    return (
      <section aria-label="最近的片段" className="homeRecentFragment homeRecentFragment-empty">
        <p>新的旅程还没有留下太多痕迹。</p>
      </section>
    );
  }

  return (
    <section aria-labelledby="home-recent-fragment-title" className="homeRecentFragment">
      <h2 id="home-recent-fragment-title">最近的片段</h2>
      <div className="homeFragmentLine">
        <p title={fragment.text}>{fragment.text}</p>
        <span aria-hidden="true" />
        {fragment.time ? <time>{fragment.time}</time> : null}
      </div>
    </section>
  );
}
