import type { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "quiet" | "ghost" | "danger";
type ButtonSize = "small" | "medium";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  iconOnly?: boolean;
  size?: ButtonSize;
  variant?: ButtonVariant;
};

export function Button({
  className = "",
  iconOnly = false,
  size = "medium",
  type = "button",
  variant = "secondary",
  ...props
}: ButtonProps) {
  return (
    <button
      className={`uiButton uiButton-${variant} uiButton-${size}${iconOnly ? " uiButton-iconOnly" : ""}${
        className ? ` ${className}` : ""
      }`}
      type={type}
      {...props}
    />
  );
}
