type JourneyTrailProps = {
  quiet?: boolean;
};

export function JourneyTrail({ quiet = false }: JourneyTrailProps) {
  return (
    <svg
      aria-hidden="true"
      className={`journeyTrail${quiet ? " journeyTrail-quiet" : ""}`}
      preserveAspectRatio="none"
      viewBox="0 0 44 620"
    >
      <path d="M13 0 C13 72 35 78 22 160 C10 232 38 248 25 330 C13 410 34 428 22 510 C17 551 22 584 22 620" />
      <circle cx="22" cy="154" r="5" />
      {!quiet ? <circle cx="25" cy="326" r="5" /> : null}
      {!quiet ? <circle cx="22" cy="506" r="5" /> : null}
    </svg>
  );
}
