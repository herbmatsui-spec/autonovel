import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Modal } from './Modal';
import { ExportHandoffSummary, ExportTarget } from '../../types/export';

interface ExportConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  summary: ExportHandoffSummary;
  onConfirm: (target: ExportTarget) => void;
}

export function ExportConfirmModal({
  isOpen,
  onClose,
  summary,
  onConfirm,
}: ExportConfirmModalProps) {
  if (!isOpen || !summary) return null;

  const [isOpenState, setIsOpenState] = useState(isOpen);
  const focusTrapRef = useRef<HTMLElement>(null);
  const firstFocusableRef = useRef<HTMLElement | null>(null);
  const lastFocusableRef = useRef<HTMLElement | null>(null);

  // モーダルが開いたときにフォーカスを管理
  useEffect(() => {
    if (!isOpenState) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          // Shift + Tab
          if (document.activeElement === firstFocusableRef.current) {
            e.preventDefault();
            lastFocusableRef.current?.focus();
          }
        } else {
          // Tab
          if (document.activeElement === lastFocusableRef.current) {
            e.preventDefault();
            firstFocusableRef.current?.focus();
          }
        }
      }
      // ESC キーでの閉じ処理は Modal コンポーネント側で処理されるため、ここでは何もしない
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpenState, onClose, firstFocusableRef, lastFocusableRef]);

  // 初期フォーカスを設定
  useEffect(() => {
    if (isOpenState) {
      firstFocusableRef.current?.focus();
    }
  }, [isOpenState, firstFocusableRef]);

  return (
    <Modal 
      isOpen={isOpenState} 
      onClose={onClose} 
      title="出力前確認"
      ref={focusTrapRef}
    >
      <div className="space-y-6">
        {/* 警告表示 */}
        {summary.warnings.length > 0 && (
          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
            <h3 className="font-medium text-yellow-800">注意</h3>
            <p className="mt-2 text-sm text-yellow-700">
              {summary.warnings.map((w, i) => (
                <p key={i}>• {w}</p>
              ))}
            </p>
          </div>
        )}

        {/* 対象サマリー */}
        <div className="space-y-4">
          {summary.targets.map((target, index) => (
            <div
              key={index}
              className={`border rounded-lg p-4 ${
                index === 0 ? 'border-primary' : 'border-gray-200'
              }`}
            >
              <h3 className="font-semibold">{target.label}</h3>
              <div className="grid grid-cols-2 gap-4 text-sm text-gray-600 mt-2">
                <div>
                  <div className="font-medium">ブランチ</div>
                  <div>{target.branchId}</div>
                </div>
                <div>
                  <div className="font-medium">版</div>
                  <div>{target.version === 'saved' ? '保存版' : '現在編集版'}</div>
                </div>
                <div>
                  <div className="font-medium">行き先</div>
                  <div>
                    {target.destination === 'zip'
                      ? 'ZIPダウンロード'
                      : target.destination === 'epub'
                        ? 'EPUBダウンロード'
                        : target.destination === 'clipboard'
                          ? 'クリップボードコピー'
                          : '出版'}
                  </div>
                </div>
                <div>
                  <div className="font-medium">文字数</div>
                  <div>{target.wordCount.toLocaleString()}字</div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* プライマリターゲット詳細（最初のターゲット） */}
        {summary.targets.length > 0 && (
          <div className="bg-primary-50 border border-primary-200 rounded-lg p-4">
            <h3 className="font-medium text-primary-800 flex items-center gap-2">
              📤 出力実行対象
            </h3>
            <p className="mt-2 text-sm">
              {summary.primaryTarget.label} を出力します
            </p>
          </div>
        )}
      </div>

      <div className="modal-actions justify-end space-x-3">
        <button
          ref={firstFocusableRef}
          onClick={onClose}
          className="btn btn-outline"
        >
          キャンセル
        </button>
        <button
          ref={lastFocusableRef}
          onClick={() => onConfirm(summary.primaryTarget)}
          className="btn btn-primary"
        >
          出力実行
        </button>
      </div>
    </Modal>
  );
}