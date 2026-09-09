import * as React from "react";
import { EditorSnapshot } from "../../types/history";

interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  snapshots: EditorSnapshot[];
  currentText: string;
  onSnapshotSelect: (snapshotId: string | null) => void;
  onRestore: (snapshotId: string) => void;
}

export const HistoryDrawer: React.FC<HistoryDrawerProps> = ({
  isOpen,
  onClose,
  snapshots,
  currentText,
  onSnapshotSelect,
  onRestore,
}) => {
  const [selectedSnapshotId, setSelectedSnapshotId] = React.useState<string | null>(null);

  // Sort snapshots by timestamp descending (newest first)
  const sortedSnapshots = React.useMemo(() => {
    return [...snapshots].sort((a, b) => b.timestamp - a.timestamp);
  }, [snapshots]);

  // Find selected snapshot
  const selectedSnapshot = sortedSnapshots.find(
    (snap) => snap.id === selectedSnapshotId
  );

  // Format timestamp to HH:mm:ss
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  };

  // Calculate character count difference
  const getCharCountDiff = (snapshot: EditorSnapshot): string => {
    const diff = snapshot.charCount - currentText.length;
    const absDiff = Math.abs(diff);
    const sign = diff >= 0 ? "+" : "-";
    return `${sign}${absDiff.toLocaleString()}字`;
  };

  // Get label badge color based on source
  const getLabelColor = (source: EditorSnapshot['source']): string => {
    switch (source) {
      case "ai_assist":
        return "var(--ai-assist-color, #8b5cf6)"; // purple
      case "ai_generate":
        return "var(--ai-generate-color, #ec4899)"; // pink
      case "autosave":
        return "var(--autosave-color, #6b7280)"; // gray
      case "manual":
      default:
        return "var(--manual-color, #3b82f6)"; // blue
    }
  };

  if (!isOpen) {
    return null;
  }

  // Prepare preview text if a snapshot is selected
  let previewContent = null;
  if (selectedSnapshot) {
    const lines = selectedSnapshot.text.split("\n");
    const previewLines = lines.slice(0, 10);
    const previewText = previewLines.join("\n");
    const hasMore = lines.length > 10;
    previewContent = (
      <>
        <div style={{ fontSize: "14px", fontWeight: "600", marginBottom: "8px" }}>
          プレビュー（冒頭10行）
        </div>
        <div
          style={{
            maxHeight: "200px",
            overflowY: "auto",
            backgroundColor: "var(--bg-input)",
            borderRadius: "4px",
            padding: "12px",
            fontFamily: "monospace",
            whiteSpace: "pre-wrap",
            wordWrap: "break-word",
          }}
        >
          {previewText}
          {hasMore && (
            <div style={{ textAlign: "center", marginTop: "8px", color: "var(--text-muted)", fontSize: "12px" }}>
              ...{lines.length - 10}行以上を表示
            </div>
          )}
        </div>
      </>
    );
  }

  return (
    <>
      <div
        className="history-drawer-overlay"
        onClick={onClose}
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.5)",
          backdropFilter: "blur(4px)",
          zIndex: 1000,
        }}
      />
      <div
        className="history-drawer"
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          width: "380px",
          height: "100%",
          backgroundColor: "var(--bg-card)",
          borderLeft: "1px solid var(--border-color)",
          zIndex: 1001,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div className="history-drawer-header" style={{
          padding: "16px",
          borderBottom: "1px solid var(--border-color)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}>
          <h3 style={{ margin: 0, fontSize: "16px" }}>⏱️ バージョン履歴・タイムマシン</h3>
          <button onClick={onClose} style={{
            background: "transparent",
            border: "none",
            fontSize: "20px",
            cursor: "pointer",
            color: "var(--text-muted)",
          }}>
            ×
          </button>
        </div>
        <div className="history-drawer-content" style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
          {sortedSnapshots.length === 0 ? (
            <p style={{ color: "var(--text-muted)", textAlign: "center" }}>
              スナップショットがありません
            </p>
          ) : (
            <>
              {sortedSnapshots.map((snapshot) => (
                <div
                  key={snapshot.id}
                  onClick={() => {
                    setSelectedSnapshotId(snapshot.id);
                    onSnapshotSelect(snapshot.id);
                  }}
                  style={{
                    border: "1px solid var(--border-color)",
                    borderRadius: "8px",
                    padding: "12px",
                    marginBottom: "12px",
                    backgroundColor: "var(--bg-muted)",
                    cursor: "pointer",
                    opacity: selectedSnapshotId === snapshot.id ? 0.9 : 1,
                    transition: "opacity 0.2s",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <div>
                      <span
                        style={{
                          backgroundColor: getLabelColor(snapshot.source),
                          color: "white",
                          fontSize: "10px",
                          fontWeight: "bold",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          marginRight: "8px",
                        }}
                      >
                        {snapshot.label}
                      </span>
                      <span style={{ fontSize: "14px", fontWeight: "600" }}>
                        第{snapshot.ep_num}話
                      </span>
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      {formatTime(snapshot.timestamp)}
                    </div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "var(--text-muted)" }}>
                    <span>{snapshot.charCount.toLocaleString()}字</span>
                    <span>{getCharCountDiff(snapshot)}</span>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
        {previewContent && (
          <div className="history-drawer-preview" style={{
            borderTop: "1px solid var(--border-color)",
            padding: "16px",
            backgroundColor: "var(--bg-card)",
          }}>
            {previewContent}
            <button
              onClick={() => {
                if (selectedSnapshotId) {
                  onRestore(selectedSnapshotId);
                }
              }}
              style={{
                marginTop: "12px",
                padding: "8px 16px",
                backgroundColor: "var(--accent-color)",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              ↩ このバージョンに復元する
            </button>
          </div>
        )}
      </div>
    </>
  );
};