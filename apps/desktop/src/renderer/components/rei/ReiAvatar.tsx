export type ReiPresenceState = "idle" | "listening" | "thinking" | "speaking";
type ReiAvatarSize = "small" | "medium" | "large";

type ReiAvatarProps = {
  className?: string;
  label?: string;
  name?: string;
  size?: ReiAvatarSize;
  state?: ReiPresenceState;
};

export function ReiAvatar({
  className = "",
  label,
  name = "Rei",
  size = "medium",
  state = "idle"
}: ReiAvatarProps) {
  const accessibleProps = label ? { "aria-label": label, role: "img" } : { "aria-hidden": true as const };

  return (
    <span
      className={`reiAvatar reiAvatar-${size} reiAvatar-${state}${className ? ` ${className}` : ""}`}
      data-presence-state={state}
      {...accessibleProps}
    >
      <span className="reiAvatarMark">{name.trim().slice(0, 1) || "R"}</span>
    </span>
  );
}
