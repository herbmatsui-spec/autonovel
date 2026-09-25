import React, { useState, useEffect } from 'react';
import { DiffViewer } from './DiffViewer';

interface InlineRevisionDiffModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApply: () => void;
  onReject: () => void;
  onHold: () => void;
  onRegenerate: () => void;
  originalText: string;
  revisedText: string;
  validationMessage?: string;
  isValidating?: boolean;
  isValid?: boolean;
  onApplyConfirmed?: () => void;
}

export const InlineRevisionDiffModal: React.FC<InlineRevisionDiffModalProps> = ({
  isOpen,
  onClose,
  onApply,
  onReject,
  onHold,
  onRegenerate,
  originalText,
  revisedText,
  validationMessage,
  isValidating,
  isValid = true,
  onApplyConfirmed,
}) => {
  const [showApplyConfirm, setShowApplyConfirm] = useState(false);

  useEffect(() => {
    if (isOpen && !isValid && validationMessage) {
      setShowApplyConfirm(true);
    }
  }, [isOpen, isValid, validationMessage]);

  if (!isOpen) return null;

  const handleApply = () => {
    if (!isValid && validationMessage) {
      setShowApplyConfirm(true);
      return;
    }
    onApply();
    onApplyConfirmed?.();
    onClose();
  };

  const handleHold = () => {
    onHold();
    onClose();
  };

  const handleReject = () => {
    onReject();
    onClose();
  };

  const handleRegenerate = () => {
    onRegenerate();
  };

  const handleConfirmApply = () => {
    setShowApplyConfirm(false);
    onApply();
    onApplyConfirmed?.();
    onClose();
  };

  const handleCancelApply = () => {
    setShowApplyConfirm(false);
  };

  if (!isOpen) return null;

  return (
    <div className="inline-revision-modal-overlay" onClick={onClose}>
      <div className="inline-revision-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>推敲結果の確認</h3>
          <button className="close-button" onClick={onClose} aria-label="閉じる">
            ×
          </button>
        </div>

        <div className="modal-body">
          <DiffViewer
            original={originalText}
            revised={revisedText}
            showLineNumbers={false}
            granularity="char"
          />

          {!isValid && validationMessage && (
            <div className="validation-message warning">
              ⚠ {validationMessage}
              <div className="validation-detail">
                原文が編集中に変更されています。適用すると意図しない変更が含まれる可能性があります。
              </div>
            </div>
          )}

          {isValidating && (
            <div className="validating-indicator">
              原文との整合性を検証中...
            </div>
          )}

          {showApplyConfirm && (
            <div className="apply-confirm-dialog">
              <div className="confirm-content">
                <h4>原文が変更されています</h4>
                <p>選択範囲の元のテキストが編集されています。このまま適用しますか？</p>
                <div className="confirm-buttons">
                  <button className="btn btn-danger" onClick={handleCancelApply}>
                    キャンセル
                  </button>
                  <button className="btn btn-primary" onClick={handleConfirmApply}>
                    それでも適用
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button
            className="btn btn-secondary"
            onClick={onRegenerate}
            disabled={true}
            title="未実装"
          >
            再生成
          </button>
          <button className="btn btn-secondary" onClick={handleHold}>
            保留
          </button>
          <button className="btn btn-danger" onClick={handleReject}>
            却下
          </button>
          <button className="btn btn-primary" onClick={handleApply}>
            {showApplyConfirm ? 'それでも適用' : '適用'}
          </button>
        </div>
      </div>
    </div>
  );
}