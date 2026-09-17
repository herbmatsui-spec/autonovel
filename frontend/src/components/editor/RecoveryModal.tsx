import React from "react";
import { EditorSnapshot } from "../../types/editorSnapshot";

interface RecoveryModalProps {
  isOpen: boolean;
  snapshot: EditorSnapshot | null;
  onRestore: (recoveredText: string) => void;
  onDiscard: () => void;
}

export const RecoveryModal: React.FC<RecoveryModalProps> = ({
  isOpen,
  snapshot,
  onRestore,
  onDiscard,
}) => {
  if (!isOpen || !snapshot) return null;

  const savedTimeStr = new Date(snapshot.updatedAt).toLocaleString("ja-JP");

  return (
    <div className="modal-overlay" style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.6)", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="modal-content" style={{ backgroundColor: "#1e1e24", padding: "24px", borderRadius: "12px", maxWidth: "500px", width: "90%", color: "#fff" }}>
        <h3 style={{ margin: "0 0 12px 0", color: "#f59e0b" }}>⚠️ 未保存のローカル原稿が見つかりました</h3>
        <p style={{ fontSize: "14px", color: "#d1d5db", lineHeight: 1.5 }}>
          ブラウザが予期せず終了した可能性があります。以下のスナップショットから原稿を復元しますか？
        </p>
        <div style={{ background: "#2a2b36", padding: "12px", borderRadius: "8px", margin: "16px 0", fontSize: "13px" }}>
          <div>保存日時: {savedTimeStr}</div>
          <div>文字数: {snapshot.charCount} 文字</div>
        </div>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
          <button
            onClick={onDiscard}
            style={{ padding: "8px 16px", borderRadius: "6px", border: "1px solid #4b5563", background: "transparent", color: "#9ca3af", cursor: "pointer" }}
          >
            破棄してサーバー版を使用
          </button>
          <button
            onClick={() => onRestore(snapshot.content)}
            style={{ padding: "8px 16px", borderRadius: "6px", border: "none", background: "#3b82f6", color: "#fff", cursor: "pointer", fontWeight: 600 }}
          >
            原稿を復元する
          </button>
        </div>
      </div>
    </div>
  );
};