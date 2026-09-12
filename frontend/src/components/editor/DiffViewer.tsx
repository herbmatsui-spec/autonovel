import React from "react";
import { DiffChunk } from "../../types/editor";

interface DiffViewerProps {
  chunk: DiffChunk;
  onApply: () => void;
  onReject: () => void;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({ chunk, onApply, onReject }) => {
  return (
    <div 
      className="diff-viewer-overlay" 
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 2000,
        backdropFilter: "blur(4px)",
      }}
    >
      <div 
        style={{
          background: "var(--card-bg, #18181b)",
          border: "1px solid var(--border-color, #27272a)",
          borderRadius: "12px",
          width: "// 90%",
          maxWidth: "700px",
          padding: "24px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
        }}
      >
        <h3 style={{ marginTop: 0, marginBottom: "16px", color: "var(--accent-primary, #a78bfa)", fontSize: "1.1rem" }}>
          ✨ AI修正案の確認
        </h3>
        
        <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "24px" }}>
          <div>
            <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>
              変更前
            </label>
            <div 
              style={{ 
                backgroundColor: "rgba(239, 68, 68, 0.1)", 
                border: "1px solid rgba(239, 68, 68, 0.3)", 
                borderRadius: "6px", 
                padding: "12px", 
                color: "#fca5a5", 
                fontSize: "0.9rem", 
                whiteSpace: "pre-wrap",
                lineHeight: "1.6"
              }}
            >
              {chunk.original}
            </div>
          </div>

          <div>
            <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>
              修正案
            </label>
            <div 
              style={{ 
                backgroundColor: "rgba(34, 197, 94, 0.1)", 
                border: "1px solid rgba(34, 197, 94, 0.3)", 
                borderRadius: "6px", 
                padding: "12px", 
                color: "#86efac", 
                fontSize: "0.9rem", 
                whiteSpace: "pre-wrap",
                lineHeight: "1.6"
              }}
            >
              {chunk.replacement}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
          <button 
            onClick={onReject}
            style={{ 
              padding: "8px 16px", 
              borderRadius: "6px", 
              background: "transparent", 
              border: "1px solid var(--border-color)", 
              color: "var(--text-muted)", 
              cursor: "pointer",
              fontSize: "0.85rem"
            }}
          >
            却下する
          </button>
          <button 
            onClick={onApply}
            style={{ 
              padding: "8px 16px", 
              borderRadius: "6px", 
              background: "var(--accent-primary, #a78bfa)", 
              border: "none", 
              color: "white", 
              cursor: "pointer",
              fontSize: "0.85rem",
              fontWeight: "bold"
            }}
          >
            この修正を適用する
          </button>
        </div>
      </div>
    </div>
  );
};
