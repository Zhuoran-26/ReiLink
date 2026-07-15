import type { HTMLAttributes, ReactNode } from "react";

type JourneyCardProps = HTMLAttributes<HTMLElement> & {
  children: ReactNode;
  label?: string;
};

export function JourneyCard({ children, className = "", label, ...props }: JourneyCardProps) {
  return (
    <article
      aria-label={label}
      className={`journeyCard${className ? ` ${className}` : ""}`}
      {...props}
    >
      {children}
    </article>
  );
}
