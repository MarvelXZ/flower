import { ButtonHTMLAttributes, forwardRef } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  iconOnly?: boolean;
};

const variantClass: Record<ButtonVariant, string> = {
  primary:   "fw-btn-primary",
  secondary: "fw-btn-secondary",
  ghost:     "fw-btn-ghost",
  danger:    "fw-btn-danger",
};

const sizeClass: Record<ButtonSize, string> = {
  sm: "fw-btn-sm",
  md: "",
  lg: "fw-btn-lg",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "secondary", size = "md", iconOnly = false, className = "", children, ...rest }, ref) => {
    const classes = [
      "fw-btn",
      variantClass[variant],
      sizeClass[size],
      iconOnly ? "fw-icon-btn" : "",
      className,
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <button ref={ref} className={classes} {...rest}>
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
