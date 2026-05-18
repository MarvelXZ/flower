import { HTMLAttributes } from "react";

type BadgeVariant = "default" | "neutral" | "accent";
type StatusTone = "ok" | "warning" | "danger" | "info" | "muted";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  variant?: BadgeVariant;
};

type StatusProps = HTMLAttributes<HTMLSpanElement> & {
  tone: StatusTone;
};

const badgeVariant: Record<BadgeVariant, string> = {
  default: "fw-badge",
  neutral: "fw-badge fw-badge-neutral",
  accent:  "fw-badge fw-badge-accent",
};

export function Badge({ variant = "default", className = "", children, ...rest }: BadgeProps) {
  return (
    <span className={`${badgeVariant[variant]} ${className}`.trim()} {...rest}>
      {children}
    </span>
  );
}

export function StatusBadge({ tone, className = "", children, ...rest }: StatusProps) {
  return (
    <span className={`fw-status fw-status-${tone} ${className}`.trim()} {...rest}>
      {children}
    </span>
  );
}
