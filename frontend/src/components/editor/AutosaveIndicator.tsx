import { SaveStatus } from "../../hooks/useAutosave";

interface AutosaveIndicatorProps {
  status: SaveStatus;
  lastSavedAt: Date | null;
}

export const AutosaveIndicator: React.FC<AutosaveIndicatorProps> = ({
  status,
  lastSavedAt,
}) => {
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });
  };

  switch (status) {
    case "saving":
      return (
        <span className="autosave-indicator autosave-indicator--saving" title="保存中...">
          <span className="spinner" style={{ width: 12, height: 12, borderWidth: 2 }} />
          <span>保存中...</span>
        </span>
      );
    case "unsaved":
      return (
        <span className="autosave-indicator autosave-indicator--unsaved" title="未保存の変更があります">
          <span style={{ color: "#f59e0b" }}>●</span>
          <span>未保存</span>
        </span>
      );
    case "saved":
    default:
      return (
        <span className="autosave-indicator autosave-indicator--saved" title={lastSavedAt ? `保存済み ${formatTime(lastSavedAt)}` : "保存済み"}>
          <span style={{ color: "#10b981" }}>✓</span>
          <span>{lastSavedAt ? `保存済み ${formatTime(lastSavedAt)}` : "保存済み"}</span>
        </span>
      );
  }
};