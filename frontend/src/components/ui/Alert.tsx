import { HTMLAttributes } from "react";

type AlertVariant = "info" | "success" | "warning" | "danger";

type AlertProps = HTMLAttributes<HTMLDivElement> & {
  variant?: AlertVariant;
  title?: string;
};

const variantClass: Record<AlertVariant, string> = {
  info:    "fw-alert",
  success: "fw-alert fw-alert-success",
  warning: "fw-alert fw-alert-warning",
  danger:  "fw-alert fw-alert-danger",
};

export function Alert({ variant = "info", title, className = "", children, ...rest }: AlertProps) {
  return (
    <div className={`${variantClass[variant]} ${className}`.trim()} {...rest}>
      {title && <span className="fw-alert-title">{title}</span>}
      {children && <span className="fw-alert-body">{children}</span>}
    </div>
  );
}
