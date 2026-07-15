import type { ElementType, HTMLAttributes, ReactNode } from "react";

export type SurfaceLevel = "canvas" | "base" | "raised" | "overlay";

export type SurfaceProps = HTMLAttributes<HTMLElement> & {
  as?: ElementType;
  children: ReactNode;
  level?: SurfaceLevel;
};

export function Surface({ as: Component = "section", children, className = "", level = "base", ...props }: SurfaceProps) {
  return (
    <Component
      className={`uiSurface uiSurface-${level}${className ? ` ${className}` : ""}`}
      data-surface-level={level}
      {...props}
    >
      {children}
    </Component>
  );
}

export function Card({ className = "", ...props }: Omit<SurfaceProps, "level">) {
  return <Surface className={`uiCard${className ? ` ${className}` : ""}`} level="raised" {...props} />;
}
