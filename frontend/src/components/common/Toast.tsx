import React from "react";
import { ToastNotification } from "../../types";

interface ToastProps {
  toast: ToastNotification;
  onClose: (id: string) => void;
}

export const Toast: React.FC<ToastProps> = ({ toast, onClose }) => {
  const getIcon = () => {
    switch (toast.type) {
      case "success":
        return "✨";
      case "error":
        return "❌";
      default:
        return "ℹ️";
    }
  };

  const getClassName = () => {
    switch (toast.type) {
      case "success":
        return "toast toast--success";
      case "error":
        return "toast toast--error";
      default:
        return "toast toast--info";
    }
  };

  // 提案2: スクリーンリーダーに通知を読み上げさせる（error は即時、他は polite）
  const ariaLive = toast.type === "error" ? "assertive" : "polite";

  return (
    <div
      className={getClassName()}
      style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
      role="status"
      aria-live={ariaLive}
      aria-atomic="true"
    >
      <div>
        <span style={{ marginRight: "8px" }}>{getIcon()}</span>
        <span>{toast.message}</span>
      </div>
      <button
        onClick={() => onClose(toast.id)}
        style={{
          background: "none",
          border: "none",
          color: "inherit",
          cursor: "pointer",
          marginLeft: "12px",
          opacity: 0.7,
        }}
        aria-label="閉じる"
      >
        ✕
      </button>
    </div>
  );
};
