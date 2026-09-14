import React from "react";
import { DiffChunk } from "../../types/editor";

interface ProseRefineDiffModalProps {
  isOpen: boolean;
  onClose: () => void;
  originalText: string;
  refinedText: string;
  chunks: DiffChunk[];
}

export const ProseRefineDiffModal: React.FC<ProseRefineDiffModalProps> = ({
  isOpen,
  onClose,
  originalText,
  refinedText,
  chunks,
}) => {
  if (!isOpen) {
    return null;
  }

  return (
    <div 
      className="modal-overlay" 
      onClick={onClose}
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
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--card-bg, #18181b)",
          border: "1px solid var(--border-color, #27272a)",
          borderRadius: "12px",
          width: "90%",
          maxWidth: "800px",
          maxHeight: "80vh",
          padding: "24px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
          overflowY: "auto",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <h2 style={{ margin: 0, color: "var(--accent-primary, #a78bfa)" }}>📝 文体推敲差分確認</h2>
          <button 
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              fontSize: "1.5rem",
              cursor: "pointer",
              width: "36px",
              height: "36px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: "50%",
            }}
          >
            ✕
          </button>
        </div>
        
        <div style={{ marginBottom: "24px" }}>
          <h3 style={{ marginTop: 0, marginBottom: "12px", color: "var(--text-muted)" }}>比較プレビュー</h3>
          <div style={{ display: "flex", gap: "24px" }}>
            <div style={{ flex: 1 }}>
              <h4 style={{ margin: "0 0 8px 0", color: "#fca5a5" }}>修正前 (Original)</h4>
              <div 
                style={{ 
                  backgroundColor: "rgba(239, 68, 68, 0.1)", 
                  border: "1px solid rgba(239, 68, 68, 0.3)", 
                  borderRadius: "8px", 
                  padding: "16px", 
                  color: "#fca5a5", 
                  fontSize: "0.95rem", 
                  whiteSpace: "pre-wrap", 
                  lineHeight: "1.8",
                  maxHeight: "200px",
                  overflowY: "auto",
                }}
              >
                {originalText}
              </div>
            </div>
            <div style={{ flex: 1 }}>
              <h4 style={{ margin: "0 0 8px 0", color: "#86efac" }}>修正後 (Refined)</h4>
              <div 
                style={{ 
                  backgroundColor: "rgba(34, 197, 94, 0.1)", 
                  border: "1px solid rgba(34, 197, 94, 0.3)", 
                  borderRadius: "8px", 
                  padding: "16px", 
                  color: "#86efac", 
                  fontSize: "0.95rem", 
                  whiteSpace: "pre-wrap", 
                  lineHeight: "1.8",
                  maxHeight: "200px",
                  overflowY: "auto",
                }}
              >
                {refinedText}
              </div>
            </div>
          </div>
        </div>
        
        {chunks && chunks.length > 0 && (
          <div>
            <h3 style={{ marginTop: 0, marginBottom: "16px", color: "var(--text-muted)" }}>詳細な変更箇所</h3>
            <div style={{ 
              backgroundColor: "rgba(30, 30, 30, 0.5)", 
              borderRadius: "8px", 
              padding: "16px",
              maxHeight: "300px",
              overflowY: "auto",
            }}>
              {chunks.map((chunk, index) => (
                <div key={index} style={{ marginBottom: "16px", paddingBottom: "12px", borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                    <span style={{ fontSize: "0.85rem", color: "#fca5a5" }}>変更前</span>
                    <span style={{ fontSize: "0.85rem", color: "#86efac" }}>変更後</span>
                  </div>
                  <div style={{ display: "flex", gap: "16px" }}>
                    <div style={{ flex: 1 }}>
                      <div 
                        style={{ 
                          backgroundColor: "rgba(239, 68, 68, 0.2)", 
                          borderRadius: "6px", 
                          padding: "12px", 
                          fontFamily: "monospace",
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        {chunk.original}
                      </div>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div 
                        style={{ 
                          backgroundColor: "rgba(34, 197, 94, 0.2)", 
                          borderRadius: "6px", 
                          padding: "12px", 
                          fontFamily: "monospace",
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        {chunk.replacement}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid rgba(255,255,255,0.1)", display: "flex", justifyContent: "flex-end", gap: "12px" }}>
          <button 
            onClick={onClose}
            style={{ 
              padding: "10px 20px", 
              borderRadius: "6px", 
              background: "transparent", 
              border: "1px solid var(--border-color)", 
              color: "var(--text-muted)", 
              cursor: "pointer",
              fontWeight: "500"
            }}
          >
            閉じる
          </button>
          <button 
            onClick={onClose}
            style={{ 
              padding: "10px 20px", 
              borderRadius: "6px", 
              background: "var(--accent-primary, #a78bfa)", 
              border: "none", 
              color: "white", 
              cursor: "pointer",
              fontWeight: "600"
            }}
          >
            了解
          </button>
        </div>
      </div>
    </div>
  );
};
