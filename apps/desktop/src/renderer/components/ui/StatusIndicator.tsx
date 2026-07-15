export type StatusTone = "neutral" | "success" | "warning" | "danger" | "active";

type StatusIndicatorProps = {
  className?: string;
  label: string;
  tone?: StatusTone;
};

export function StatusIndicator({ className = "", label, tone = "neutral" }: StatusIndicatorProps) {
  return (
    <span className={`uiStatus uiStatus-${tone}${className ? ` ${className}` : ""}`}>
      <span aria-hidden="true" className="uiStatusDot" />
      <span>{label}</span>
    </span>
  );
}
