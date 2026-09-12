import React from "react";

interface SnippetTooltipProps {
  summary: string;
  properties: Record<string, any>;
  position: { top: number; left: number };
}

export const SnippetTooltip: React.FC<SnippetTooltipProps> = ({ summary, properties, position }) => {
  return (
    <div 
      style={{
        position: "fixed",
        top: position.top,
        left: position.left,
        zIndex: 3000,
        backgroundColor: "var(--card-bg, #18181b)",
        border: "1px solid var(--accent-cyan, #38bdf8)",
        borderRadius: "8px",
        padding: "12px",
        width: "300px",
        maxWidth: "90vw",
        boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.5)",
        color: "var(--text-primary, #fff)",
        fontSize: "0.85rem",
        lineHeight: "1.5",
        pointerEvents: "none",
        transition: "opacity 0.2s ease",
      }}
    >
      <div style={{ 
        fontWeight: "bold", 
        color: "var(--accent-cyan, #38bdf8)", 
        marginBottom: "8px", 
        fontSize: "0.9rem",
        borderBottom: "1px solid var(--border-color)",
        paddingBottom: "4px"
      }}>
        キャラクター設定要約
      </div>
      <div style={{ marginBottom: "8px", whiteSpace: "pre-wrap" }}>
        {summary}
      </div>
      {Object.entries(properties).length > 0 && (
        <div style={{ 
          fontSize: "0.75rem", 
          color: "var(--text-muted)", 
          display: "flex", 
          flexDirection: "column", 
          gap: "2px",
          borderTop: "1px solid var(--border-color)",
          paddingTop: "8px"
        }}>
          {Object.entries(properties).map(([key, value]) => (
            <div key={key} style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ opacity: 0.7 }}>{key}:</span>
              <span>{String(value)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
