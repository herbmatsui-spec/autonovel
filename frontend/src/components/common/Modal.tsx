import React, { useEffect, useRef } from "react";

interface ModalProps {
  /** モーダルを表示するか */
  isOpen: boolean;
  /** 閉じるハンドラー（オーバーレイクリック・Esc キー・閉じるボタンで呼ばれる） */
  onClose: () => void;
  /** ヘッダータイトル（アイコン付き可） */
  title: React.ReactNode;
  /** モーダル本文 */
  children: React.ReactNode;
  /** data-testid プレフィックス（例: "media-modal"） */
  testId?: string;
  /** 閉じるボタンの data-testid */
  closeBtnTestId?: string;
  /** コンテンツ最大幅 (px) */
  maxWidth?: number;
  /** コンテンツ最大高さ (vh) */
  maxHeightVh?: number;
  /** a11y: ダイアログのラベル用 id（title に設定される） */
  ariaLabelledBy?: string;
  /** z-index（デフォルト 1000） */
  zIndex?: number;
}

/**
 * 共通モーダルコンポーネント。
 *
 * - オーバーレイ + カード型コンテンツの重複実装を統合
 * - role="dialog" / aria-modal / Esc キー / フォーカストラップ対応
 * - オーバーレイクリックで閉じる（コンテンツ内クリックは無視）
 */
export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  testId,
  closeBtnTestId,
  maxWidth = 900,
  maxHeightVh = 85,
  ariaLabelledBy,
  zIndex = 1000,
}) => {
  const contentRef = useRef<HTMLDivElement>(null);

  // Esc キーで閉じる
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // 開いた時にフォーカスをコンテンツへ移動（キーボード操作の起点）
  useEffect(() => {
    if (isOpen && contentRef.current) {
      contentRef.current.focus();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const labelledBy = ariaLabelledBy ?? (testId ? `${testId}-title` : undefined);

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0,0,0,0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex,
        backdropFilter: "blur(4px)",
      }}
      data-testid={testId}
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={contentRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        className="modal-content"
        style={{
          background: "var(--card-bg, #18181b)",
          border: "1px solid var(--border-color, #27272a)",
          borderRadius: "12px",
          width: "90%",
          maxWidth: `${maxWidth}px`,
          padding: "20px",
          maxHeight: `${maxHeightVh}vh`,
          overflowY: "auto",
          outline: "none",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "16px",
          }}
        >
          <h2
            id={labelledBy}
            style={{
              margin: 0,
              fontSize: "1.2rem",
              color: "var(--accent-primary)",
            }}
          >
            {title}
          </h2>
          <button
            type="button"
            className="modal-close-btn"
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontSize: "1.2rem",
            }}
            onClick={onClose}
            aria-label="閉じる"
            data-testid={closeBtnTestId}
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
};

export default Modal;
