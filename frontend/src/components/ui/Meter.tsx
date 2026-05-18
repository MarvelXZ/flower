import { HTMLAttributes, useEffect, useRef } from "react";

type MeterProps = HTMLAttributes<HTMLDivElement> & {
  value: number;
  tone?: "ok" | "warning" | "danger";
};

export function Meter({ value, tone = "ok", className = "", ...rest }: MeterProps) {
  const fillRef = useRef<HTMLSpanElement>(null);
  const pct = Math.min(100, Math.max(0, value));

  const toneClass = tone === "ok" ? "" : `is-${tone}`;

  useEffect(() => {
    if (fillRef.current) {
      fillRef.current.style.width = `${pct}%`;
    }
  }, [pct]);

  return (
    <div className={`fw-meter ${className}`.trim()} aria-label={`${pct}%`} {...rest}>
      <span ref={fillRef} className={`fw-meter-fill ${toneClass}`.trim()} />
    </div>
  );
}
