import React from "react";

interface PanelProps {
  /** パネルの見た目バリアント */
  variant?: "card" | "studio-pane" | "wizard-panel";
  /** パネルタイトル（省略可） */
  title?: React.ReactNode;
  /** パネル本文 */
  children: React.ReactNode;
  /** 追加クラス */
  className?: string;
  /** インラインスタイルの上書き（極力使わない） */
  style?: React.CSSProperties;
}

const variantClassMap: Record<NonNullable<PanelProps["variant"]>, string> = {
  card: "card",
  "studio-pane": "studio-pane card",
  "wizard-panel": "wizard-panel card",
};

/**
 * 共通パネルコンポーネント。
 * index.css の .card / .studio-pane / .wizard-panel を利用した
 * 統一されたカード UI を提供する。
 */
export const Panel: React.FC<PanelProps> = ({
  variant = "card",
  title,
  children,
  className = "",
  style,
}) => {
  const classes = [variantClassMap[variant], className]
    .filter(Boolean)
    .join(" ");

  return (
    <section className={classes} style={style}>
      {title && <h3 className="panel-title">{title}</h3>}
      {children}
    </section>
  );
};

export default Panel;
