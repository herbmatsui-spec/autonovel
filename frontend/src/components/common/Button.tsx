import React from "react";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "export"
  | "danger"
  | "success"
  | "accent-cyan"
  | "accent-purple"
  | "accent-yellow";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** ボタンの見た目バリアント（既存の .btn-* クラスに対応） */
  variant?: ButtonVariant;
  /** アイコン付きラベル用（例: "⚙️ LLM設定"） */
  children: React.ReactNode;
  /** 小サイズ（ヘッダー用など） */
  size?: "sm" | "md";
}

const variantClassMap: Record<ButtonVariant, string> = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  export: "btn-export",
  danger: "btn-danger",
  success: "btn-success",
  "accent-cyan": "btn-accent-cyan",
  "accent-purple": "btn-accent-purple",
  "accent-yellow": "btn-accent-yellow",
};

/**
 * 共通ボタンコンポーネント。
 * 既存 index.css の .btn / .btn-* クラス体系を利用し、
 * インラインスタイルの散在を解消する。
 */
export const Button: React.FC<ButtonProps> = ({
  variant = "primary",
  size = "md",
  className = "",
  children,
  type = "button",
  ...rest
}) => {
  const classes = [
    "btn",
    variantClassMap[variant],
    size === "sm" ? "btn--sm" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button type={type} className={classes} {...rest}>
      {children}
    </button>
  );
};

export default Button;
