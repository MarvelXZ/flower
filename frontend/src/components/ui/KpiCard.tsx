import { ReactNode, HTMLAttributes } from "react";
import { StatusBadge } from "./Badge";

type KpiTone = "ok" | "warning" | "danger" | "info";

type KpiCardProps = HTMLAttributes<HTMLElement> & {
  label: string;
  value: string | number;
  meta?: ReactNode;
  tone?: KpiTone;
  metaIsStatus?: boolean;
};

export function KpiCard({ label, value, meta, tone = "ok", metaIsStatus = false, className = "", ...rest }: KpiCardProps) {
  return (
    <article className={`fw-card fw-kpi ${className}`.trim()} {...rest}>
      <span className="fw-kpi-label">{label}</span>
      <strong className="fw-kpi-value">{value}</strong>
      {meta !== undefined && (
        <span className="fw-kpi-meta">
          {metaIsStatus ? (
            <StatusBadge tone={tone}>{meta}</StatusBadge>
          ) : (
            <span className="fw-dimmed">{meta}</span>
          )}
        </span>
      )}
    </article>
  );
}
