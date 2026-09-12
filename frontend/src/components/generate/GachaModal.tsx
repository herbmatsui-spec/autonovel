import React from "react";
import { GachaPlan } from "../../types/easyMode";

interface GachaModalProps {
  isOpen: boolean;
  onClose: () => void;
  plans: GachaPlan[];
  onSelectPlan: (plan: GachaPlan) => void;
}

export const GachaModal: React.FC<GachaModalProps> = ({ isOpen, onClose, plans, onSelectPlan }) => {
  if (!isOpen) return null;

  const getPlanColor = (type: GachaPlan["plan_type"]) => {
    switch (type) {
      case "royal": return "rgba(255, 215, 0, 0.2)"; // Gold
      case "curveball": return "rgba(0, 191, 255, 0.2)"; // DeepSkyBlue
      case "dark": return "rgba(139, 0, 139, 0.2)"; // DarkMagenta
      default: return "rgba(255, 255, 255, 0.1)";
    }
  };

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
        width: "// 90% max-width 800px",
        maxWidth: "800px",
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
          <h2 style={{ margin: 0, fontSize: "1.5rem", fontWeight: "bold" }}>🎲 ガチャプラン選択</h2>
          <button onClick={onClose} style={{
            background: "none",
            border: "none",
            color: "var(--text-muted, #888)",
            cursor: "pointer",
            fontSize: "1.5rem"
          }}>✕</button>
        </div>

        <div style={{ 
          display: "grid", 
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", 
          gap: "16px", 
          overflowY: "auto",
          paddingRight: "8px"
        }}>
          {plans.map((plan) => (
            <div 
              key={plan.plan_id} 
              onClick={() => onSelectPlan(plan)}
              style={{
                backgroundColor: getPlanColor(plan.plan_type),
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "12px",
                padding: "16px",
                cursor: "pointer",
                transition: "transform 0.2s, border-color 0.2s",
                display: "flex",
                flexDirection: "column",
                gap: "8px",
                position: "relative",
                overflow: "hidden"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-4px)";
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.3)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
              }}
            >
              <div style={{ 
                fontSize: "0.7rem", 
                fontWeight: "bold", 
                textTransform: "uppercase", 
                color: "var(--text-muted, #bbb)",
                marginBottom: "4px"
              }}>
                {plan.plan_type}
              </div>
              <div style={{ fontWeight: "bold", fontSize: "1.1rem", marginBottom: "4px" }}>
                {plan.title}
              </div>
              <div style={{ fontSize: "0.9rem", lineHeight: "1.4", color: "var(--text-main, #ddd)" }}>
                {plan.logline}
              </div>
              <div style={{ 
                marginTop: "12px", 
                fontSize: "0.8rem", 
                padding: "8px", 
                backgroundColor: "rgba(0,0,0,0.3)", 
                borderRadius: "6px",
                fontStyle: "italic"
              }}>
                ✨ {plan.charm_point}
              </div>
            </div>
          ))}
        </div>

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
