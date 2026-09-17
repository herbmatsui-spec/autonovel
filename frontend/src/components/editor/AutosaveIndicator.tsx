import React from "react";
import { AutoSaveStatus } from "../../types/editorSnapshot";

interface AutosaveIndicatorProps {
  status: AutoSaveStatus;
  lastSavedAt: Date | null;
}

export const AutosaveIndicator: React.FC<AutosaveIndicatorProps> = ({ status, lastSavedAt }) => {
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  switch (status) {
    case "saving":
      return (
        <span className="autosave-indicator" title="ローカル保存中...">
          <span style={{ color: "#3b82f6" }}>⏳</span>
          <span style={{ marginLeft: 4 }}>保存中...</span>
        </span>
      );
    case "offline":
      return (
        <span className="autosave-indicator" title="オフライン（端末内に安全に保存されています）">
          <span style={{ color: "#f59e0b" }}>📶❌</span>
          <span style={{ marginLeft: 4, color: "#f59e0b" }}>端末内保存 (オフライン)</span>
        </span>
      );
    case "unsaved":
      return (
        <span className="autosave-indicator" title="未保存の変更があります">
          <span style={{ color: "#ef4444" }}>●</span>
          <span style={{ marginLeft: 4 }}>未保存</span>
        </span>
      );
    case "saved":
    default:
      return (
        <span className="autosave-indicator" title={lastSavedAt ? `ローカル保存済 ${formatTime(lastSavedAt)}` : "保存済み"}>
          <span style={{ color: "#10b981" }}>✓</span>
          <span style={{ marginLeft: 4 }}>{lastSavedAt ? `保存済 ${formatTime(lastSavedAt)}` : "保存済"}</span>
        </span>
      );
  }
};