import React, { useState } from 'react';
import { apiFetch, handleResponse } from '../../api/client';
import { useToast } from '../../hooks/useToast';

interface IllustrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  bookId: number;
  chapterTitle: string;
  chapterBody: string;
}

interface IllustrationItem {
  id: string;
  type: 'character' | 'scene' | 'cover';
  prompt: string;
  imageUrl: string | null;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  error?: string;
}

export const IllustrationModal: React.FC<IllustrationModalProps> = ({
  isOpen,
  onClose,
  bookId,
  chapterTitle,
  chapterBody,
}) => {
  const [illustrations, setIllustrations] = useState<IllustrationItem[]>([
    { id: 'char-1', type: 'character', prompt: '', imageUrl: null, status: 'pending' },
    { id: 'char-2', type: 'character', prompt: '', imageUrl: null, status: 'pending' },
    { id: 'scene-1', type: 'scene', prompt: '', imageUrl: null, status: 'pending' },
    { id: 'cover-1', type: 'cover', prompt: '', imageUrl: null, status: 'pending' },
  ]);
  const [isGenerating, setIsGenerating] = useState(false);
  const { addToast } = useToast();

  const generateAll = async () => {
    setIsGenerating(true);
    try {
      const resp = await apiFetch('/api/illustrations/batch', {
        method: 'POST',
        body: JSON.stringify({
          book_id: bookId,
          chapter_title: chapterTitle,
          chapter_body: chapterBody,
        }),
      });
      const data = await handleResponse<{ illustrations: IllustrationItem[] }>(resp);
      
      setIllustrations(data.illustrations);
      addToast('✨ 画像生成が完了しました！', 'success');
    } catch (err) {
      console.error(err);
      addToast('❌ 画像生成に失敗しました', 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: '800px', width: '90%' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>📦 アセットパック生成</h2>
          <button className="modal-close" onClick={onClose} aria-label="閉じる">×</button>
        </div>
        <div className="modal-body" style={{ padding: '20px' }}>
          <div style={{ marginBottom: '16px', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
            <strong>チャプター:</strong> {chapterTitle}
          </div>
          
          <div style={{ display: 'grid', gap: '16px', marginBottom: '24px' }}>
            {illustrations.map((illust) => (
              <div key={illust.id} className="illustration-card" style={{
                border: '1px solid var(--border-color)',
                borderRadius: '12px',
                padding: '16px',
                background: 'var(--bg-card)',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span style={{
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    padding: '4px 8px',
                    borderRadius: '9999px',
                    backgroundColor: illust.type === 'character' ? 'var(--accent-primary)' :
                                   illust.type === 'scene' ? 'var(--accent-secondary)' : 'var(--accent-danger)',
                    color: 'white',
                    textTransform: 'capitalize',
                  }}>
                    {illust.type}
                  </span>
                  <span style={{
                    fontSize: '0.75rem',
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    backgroundColor: illust.status === 'completed' ? 'var(--success-bg)' :
                                   illust.status === 'generating' ? 'var(--warning-bg)' :
                                   illust.status === 'failed' ? 'var(--danger-bg)' : 'var(--muted-bg)',
                    color: illust.status === 'completed' ? 'var(--success-text)' :
                           illust.status === 'generating' ? 'var(--warning-text)' :
                           illust.status === 'failed' ? 'var(--danger-text)' : 'var(--muted-text)',
                  }}>
                    {illust.status === 'completed' ? '完了' :
                     illust.status === 'generating' ? '生成中' :
                     illust.status === 'failed' ? '失敗' : '未生成'}
                  </span>
                </div>
                
                {illust.imageUrl ? (
                  <img 
                    src={illust.imageUrl} 
                    alt={`${illust.type} illustration`}
                    style={{ 
                      width: '100%', 
                      maxHeight: '300px', 
                      objectFit: 'cover', 
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                    }}
                  />
                ) : (
                  <div style={{
                    width: '100%',
                    height: '200px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'var(--bg-secondary)',
                    borderRadius: '8px',
                    border: '2px dashed var(--border-color)',
                    color: 'var(--text-muted)',
                  }}>
                    {illust.status === 'generating' ? '🎨 生成中...' : '画像未生成'}
                  </div>
                )}
                
                {illust.error && (
                  <div style={{ marginTop: '8px', color: 'var(--accent-danger)', fontSize: '0.8rem' }}>
                    エラー: {illust.error}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
            <button
              className="btn btn-secondary"
              onClick={onClose}
              disabled={isGenerating}
            >
              閉じる
            </button>
            <button
              className="btn btn-primary"
              onClick={generateAll}
              disabled={isGenerating}
            >
              {isGenerating ? '⏳ 一括生成中...' : '🎨 一括生成 (POST /api/illustrations/batch)'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};