import React from "react";
import { LineScore } from "../../types/quality";

interface EditorGutterProps {
  /** 本文（行数計算に使用） */
  content: string;
  /** 行ごとの品質スコア（左端のカラーバー） */
  lineScores?: LineScore[];
  /** ガター内コンテナの ref（スクロール同期用） */
  gutterInnerRef: React.MutableRefObject<HTMLDivElement | null>;
  /** ガタークリックハンドラー（行ジャンプ） */
  onGutterClick: (e: React.MouseEvent<HTMLDivElement>) => void;
}

/**
 * エディタ左端の行番号ガター。
 *
 * - 行番号表示＋行ごとの品質スコアカラーバー
 * - クリックで該当行へジャンプ（Editor 側でハンドリング）
 * - Editor.tsx から分割（提案3: 巨大コンポーネント分割）
 */
export const EditorGutter: React.FC<EditorGutterProps> = ({
  content,
  lineScores,
  gutterInnerRef,
  onGutterClick,
}) => {
  return (
    <div
      className="gutter"
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        bottom: 0,
        width: "40px",
        pointerEvents: "auto",
        zIndex: 3,
        overflow: "hidden",
      }}
      onClick={onGutterClick}
    >
      <div
        ref={gutterInnerRef}
        style={{
          position: "relative",
          height: "100%",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {content.split("\n").map((line, index) => (
          <div
            key={index}
            style={{
              position: "relative",
              width: "100%",
              textAlign: "right",
              paddingRight: "8px",
              color: "var(--text-muted)",
              fontSize: "0.82rem",
              lineHeight: "1.9",
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-end",
            }}
          >
            {lineScores && lineScores[index] && (
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: "4px",
                  backgroundColor:
                    lineScores[index].level === "error"
                      ? "#ef4444"
                      : lineScores[index].level === "warning"
                        ? "#f59e0b"
                        : lineScores[index].level === "info"
                          ? "#10b981"
                          : "#10b981",
                }}
              />
            )}
            {index + 1}
          </div>
        ))}
      </div>
    </div>
  );
};

export default EditorGutter;
