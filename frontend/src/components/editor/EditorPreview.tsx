import React from "react";

interface EditorPreviewProps {
  /** プレビューする本文 */
  content: string;
  /** ミラーハイライトモード（textarea 背面の重ね描き）か ルビプレビューモードか */
  mode: "mirror" | "ruby";
  /** mirror 用: エディタの共通クラス名 */
  editorClassName?: string;
  /** mirror 用: ミラー div の ref（スクロール同期） */
  mirrorRef?: React.MutableRefObject<HTMLDivElement | null>;
}

/**
 * ルビ記法 ｜親文字《ルビ》 を HTML に変換する簡易パーサー
 */
export function renderRuby(text: string): { __html: string } {
  const formatted = text
    .replace(/｜(.+?)《(.+?)》/g, "<ruby>$1<rt>$2</rt></ruby>")
    .replace(/\n/g, "<br />");
  return { __html: formatted };
}

/**
 * キャラクター名（カタカナ語）をハイライトする簡易実装
 */
export function renderHighlightedContent(text: string): { __html: string } {
  const highlighted = text.replace(/([ァ-ヶー]+)/g, (match) => {
    return `<span class="character-name">${match}</span>`;
  });
  return { __html: highlighted };
}

/**
 * エディタのプレビューレイヤー。
 *
 * - "ruby": ルビ記法を展開した読書プレビュー
 * - "mirror": textarea 背面に重ねるハイライトミラー
 *
 * Editor.tsx から分割（提案3: 巨大コンポーネント分割）。
 */
export const EditorPreview: React.FC<EditorPreviewProps> = ({
  content,
  mode,
  editorClassName,
  mirrorRef,
}) => {
  if (mode === "mirror") {
    return (
      <div
        ref={mirrorRef}
        className={editorClassName}
        style={{
          position: "absolute",
          left: 40, // same as textarea left padding
          top: 0,
          right: 0,
          bottom: 0,
          pointerEvents: "none",
          zIndex: 2,
          whiteSpace: "pre-wrap",
          wordWrap: "break-word",
          lineHeight: "1.9",
          padding: "12px 12px 12px 40", // same as textarea
          boxSizing: "border-box",
          color: "var(--text-primary, #fff)",
          overflow: "hidden",
        }}
      >
        <div dangerouslySetInnerHTML={renderHighlightedContent(content)} />
      </div>
    );
  }

  return (
    <div
      className="output-area"
      style={{
        flex: 1,
        minHeight: "280px",
        overflowY: "auto",
        lineHeight: "1.9",
        letterSpacing: "0.05em",
      }}
      dangerouslySetInnerHTML={renderRuby(content || "本文がありません。")}
      data-testid="editor-preview"
    />
  );
};

export default EditorPreview;
