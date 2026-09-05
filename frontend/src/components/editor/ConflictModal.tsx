import React, { useState } from "react";
import { ConflictSection } from "../../hooks/_unused/useCollabSync";

interface ConflictModalProps {
  conflicts: ConflictSection[];
  onResolve: (resolutions: Record<number, "server" | "client">) => void;
  onCancel: () => void;
}

export const ConflictModal: React.FC<ConflictModalProps> = ({
  conflicts,
  onResolve,
  onCancel,
}) => {
  const [choices, setChoices] = useState<Record<number, "server" | "client">>({});

  const handleChoice = (index: number, choice: "server" | "client") => {
    setChoices((prev) => ({ ...prev, [index]: choice }));
  };

  const handleApply = () => {
    onResolve(choices);
  };

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <h3>⚠ 競合が検出されました（{conflicts.length}箇所）</h3>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "12px" }}>
          各段落で「サーバ版」か「自分の版」のどちらを採用するか選んでください。
        </p>
        <div style={{ maxHeight: "400px", overflowY: "auto" }}>
          {conflicts.map((c) => (
            <div key={c.index} className="conflict-block" style={{ marginBottom: "16px", padding: "12px", border: "1px solid var(--border-color)", borderRadius: "8px" }}>
              <div style={{ display: "flex", gap: "16px" }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px", cursor: "pointer" }}>
                    <input
                      type="radio"
                      name={`conflict-${c.index}`}
                      value="server"
                      checked={choices[c.index] === "server"}
                      onChange={() => handleChoice(c.index, "server")}
                    />
                    <strong>サーバ版</strong>
                  </label>
                  <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.85rem", background: "rgba(0,0,0,0.2)", padding: "8px", borderRadius: "4px", maxHeight: "150px", overflow: "auto" }}>
                    {c.server_text || "(空)"}
                  </pre>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px", cursor: "pointer" }}>
                    <input
                      type="radio"
                      name={`conflict-${c.index}`}
                      value="client"
                      checked={choices[c.index] === "client"}
                      onChange={() => handleChoice(c.index, "client")}
                    />
                    <strong>自分の版</strong>
                  </label>
                  <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.85rem", background: "rgba(0,0,0,0.2)", padding: "8px", borderRadius: "4px", maxHeight: "150px", overflow: "auto" }}>
                    {c.client_text || "(空)"}
                  </pre>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "16px" }}>
          <button type="button" className="btn-secondary" onClick={onCancel}>
            キャンセル
          </button>
          <button type="button" className="btn-primary" onClick={handleApply} disabled={Object.keys(choices).length < conflicts.length}>
            適用して同期
          </button>
        </div>
      </div>
    </div>
  );
};