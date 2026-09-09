import React, { useState } from "react";
import { styleSamples } from "../../constants/styleSamples";
import { StyleTuningSliders } from "./StyleTuningSliders";
import { StyleTuningParams } from "../../types/styleComparison";

interface StyleComparisonModalProps {
  onClose: () => void;
}

export const StyleComparisonModal: React.FC<StyleComparisonModalProps> = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState<"action" | "dialogue" | "psychology">("action");
  const [styleParams, setStyleParams] = useState<StyleTuningParams>({
    kemeritsu: 3,
    bodyStop: 50,
    metaphor: 50,
  });
  const [customStyles, setCustomStyles] = useState<Array<{id: string; name: string; params: StyleTuningParams}>>(() => {
    const saved = localStorage.getItem("customStyles");
    return saved ? JSON.parse(saved) : [];
  });

  const scene = styleSamples.find((s) => s.id === activeTab);
  if (!scene) {
    return null;
  }

  // Simulate styled text based on parameters (in real app, this would come from backend)
  const getStyledText = (): string => {
    // For now, just return the standard text with a note
    return `${scene.standardText}\n\n[スタイル適用: ケレン味${styleParams.kemeritsu}, 体言止め${styleParams.bodyStop}%, 比喩${styleParams.metaphor}%]`;
  };

  const handleSaveAsCustom = () => {
    const name = window.prompt("カスタム文体の名前を入力してください");
    if (name) {
      const newStyle = {
        id: `custom_${Date.now()}`,
        name,
        params: styleParams,
      };
      setCustomStyles([...customStyles, newStyle]);
      localStorage.setItem("customStyles", JSON.stringify([...customStyles, newStyle]));
      window.alert(`カスタム文体「${name}」を保存しました`);
    }
  };

  const handleApplyStyle = () => {
    window.alert(`文体スタイルを適用しました！\nケレン味: ${styleParams.kemeritsu}\n体言止め: ${styleParams.bodyStop}%\n比喩: ${styleParams.metaphor}%`);
    // TODO: Actually apply the style to the novel context
  };

  return (
    <div className="style-comparison-modal">
      <div className="style-comparison-modal-content">
        <div className="style-comparison-modal-header">
          <h2>🎨 作家性DNA・文体Before/Afterプレビュー</h2>
          <button className="style-comparison-modal-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="style-comparison-modal-body">
          <div className="style-comparison-tabs">
            {["action", "dialogue", "psychology"].map((tabId) => {
              const tab = styleSamples.find((s) => s.id === tabId);
              return (
                <button
                  key={tabId}
                  onClick={() => setActiveTab(tabId as "action")}
                  className={activeTab === tabId ? "active" : ""}
                >
                  {tab?.title}
                </button>
              );
            })}
          </div>
          <div className="style-comparison-cards">
            <div className="style-comparison-card">
              <h3>標準文体 (Before)</h3>
              <p>{scene.standardText}</p>
            </div>
            <div className="style-comparison-card">
              <h3>選択文体 (After)</h3>
              <div className="style-comparison-text-after">
                <p>{getStyledText()}</p>
                {/* TODO: Implement actual highlighting */}
              </div>
              <div className="style-comparison-metrics">
                <span className="metric-badge">平均文長: 24文字/文</span>
                <span className="metric-badge">体言止め率: 35%</span>
                <span className="metric-badge">会話文比率: 42%</span>
                <span className="metric-badge">ケレン味強度: Lv.4 圧倒的無双</span>
              </div>
              <StyleTuningSliders onChange={setStyleParams} />
              <div className="style-comparison-actions">
                <button onClick={handleSaveAsCustom} className="style-comparison-save-custom">
                  💾 カスタム文体としてライブラリ保存
                </button>
                <button onClick={handleApplyStyle} className="style-comparison-apply">
                  ✨ この文体スタイルを採用
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};