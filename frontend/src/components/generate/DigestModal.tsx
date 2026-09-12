import React from "react";
import { DigestResponse } from "../../types/easyMode";

interface DigestModalProps {
  isOpen: boolean;
  onClose: () => void;
  digest: DigestResponse | null;
}

export const DigestModal: React.FC<DigestModalProps> = ({ isOpen, onClose, digest }) => {
  if (!isOpen) return null;

  return (
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      width: "100%",
      height: "100%",
      backgroundColor: "rgba(0, 0, 0, 0.7)",
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      zIndex: 1000,
      backdropFilter: "blur(4px)",
    }}>
      <div style={{
        backgroundColor: "var(--bg-main, #1a1a1a)",
        color: "var(--text-main, #eee)",
        width: "90%",
        maxWidth: "700px",
        maxHeight: "80vh",
        borderRadius: "16px",
        padding: "24px",
        boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
        border: "1px solid rgba(255,255,255,0.1)",
        display: "flex",
        flexDirection: "column",
        gap: "20px",
        overflow: "hidden"
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0, fontSize: "1.5rem", fontWeight: "bold" }}>📖 ストーリーダイジェスト</h2>
          <button onClick={onClose} style={{
            background: "none",
            border: "none",
            color: "var(--text-muted, #888)",
            cursor: "pointer",
            fontSize: "1.5rem"
          }}>✕</button>
        </div>

        {!digest ? (
          <div style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
            ダイジェスト情報を読み込み中です...
          </div>
        ) : (
          <div style={{ 
            overflowY: "auto", 
            paddingRight: "12px",
            display: "flex",
            flexDirection: "column",
            gap: "24px"
          }}>
            <section>
              <h3 style={{ fontSize: "1.1rem", color: "var(--text-muted)", marginBottom: "8px", borderLeft: "4px solid var(--accent-color, #4ade80)", paddingLeft: "8px" }}>
                タイトル
              </h3>
              <div style={{ fontSize: "1.3rem", fontWeight: "bold" }}>{digest.title}</div>
            </section>

            <section>
              <h3 style={{ fontSize: "1.1rem", color: "var(--text-muted)", marginBottom: "8px", borderLeft: "4px solid var(--accent-color, #4ade80)", paddingLeft: "8px" }}>
                あらすじ
              </h3>
              <div style={{ fontSize: "1rem", lineHeight: "1.6", whiteSpace: "pre-wrap" }}>{digest.synopsis}</div>
            </section>

            <section>
              <h3 style={{ fontSize: "1.1rem", color: "var(--text-muted)", marginBottom: "8px", borderLeft: "4px solid var(--accent-color, #4ade80)", paddingLeft: "8px" }}>
                第1話 冒頭
              </h3>
              <div style={{ 
                fontSize: "0.95rem", 
                lineHeight: "1.6", 
                whiteSpace: "pre-wrap", 
                backgroundColor: "rgba(0,0,0,0.2)", 
                padding: "12px", 
                borderRadius: "8px",
                border: "1px solid rgba(255,255,255,0.05)"
              }}>
                {digest.episode_1_text}
              </div>
            </section>

            <section>
              <h3 style={{ fontSize: "1.1rem", color: "var(--text-muted)", marginBottom: "8px", borderLeft: "4px solid var(--accent-color, #4ade80)", paddingLeft: "8px" }}>
                クライマックス・プレビュー
              </h3>
              <div style={{ 
                fontSize: "0.95rem", 
                lineHeight: "1.6", 
                whiteSpace: "pre-wrap", 
                backgroundColor: "rgba(74, 222, 128, 0.05)", 
                padding: "12px", 
                borderRadius: "8px",
                border: "1px solid rgba(74, 222, 128, 0.2)",
                fontStyle: "italic"
              }}>
                {digest.climax_preview_text}
              </div>
            </section>
          </div>
        )}

        <div style={{ textAlign: "right" }}>
          <button onClick={onClose} style={{
            padding: "8px 16px",
            borderRadius: "8px",
            border: "1px solid rgba(255,255,255,0.2)",
            backgroundColor: "rgba(255,255,255,0.1)",
            color: "var(--text-main, #eee)",
            cursor: "pointer"
          }}>
            閉じる
          </button>
        </div>
      </div>
    </div>
  );
};
