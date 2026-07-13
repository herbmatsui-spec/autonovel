import React from 'react';
import { Button } from '@/components/ui/button';
import { LoadingState } from '@/components/ui/LoadingState';
import { EmptyState } from '@/components/ui/EmptyState';
import { StatusMessage } from '@/components/ui/StatusMessage';
import { Book } from '../types';
import { useBooks } from '../hooks/useBooks';

interface BooksTabProps {
  selectedBook: any; // Temporary any, will refine
  setSelectedBook: (book: Book) => void;
  setShowCreateModal: (show: boolean) => void;
}

export function BooksTab({ selectedBook, setSelectedBook, setShowCreateModal }: BooksTabProps) {
  const { books, loading: booksLoading, error: booksError, handleDeleteBook } = useBooks();

  return (
    <div className="animate-fade-in flex flex-col gap-8">
      <div className="flex justify-between items-center">
        <div>
          <h3 style={{ fontSize: '1.2rem', color: '#fff' }}>作成済みの小説一覧</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>現在データベースに保存されている小説の企画及び執筆データです。</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          ➕ 新規自動生成 (かんたんモード)
        </Button>
      </div>

      {booksError && (
        <StatusMessage type="error" message={`小説一覧の読み込みに失敗しました: ${booksError}`} />
      )}

      {booksLoading && books.length === 0 ? (
        <LoadingState message="小説一覧を読み込み中..." icon="📚" />
      ) : books.length === 0 ? (
        <EmptyState
          icon="🏰"
          title="登録されている小説企画がありません"
          description="「新規自動生成」から最初の小説を作成してください。"
          action={{ label: '➕ 新規自動生成', onClick: () => setShowCreateModal(true) }}
        />
      ) : (
        <div className="grid gap-6" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
          {books.map((book) => {
            const isActive = selectedBook?.id === book.id;
            return (
              <div 
                key={book.id} 
                className="glass-panel" 
                onClick={() => setSelectedBook(book)}
                style={{ 
                  padding: '1.75rem', 
                  cursor: 'pointer', 
                  borderColor: isActive ? 'var(--accent-indigo)' : 'var(--border)',
                  boxShadow: isActive ? 'var(--shadow-glow)' : 'none',
                  position: 'relative'
                }}
              >
                <h4 style={{ fontSize: '1.15rem', marginBottom: '0.5rem', color: '#fff' }}>{book.title}</h4>
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                  <span className="badge badge-purple">{book.genre}</span>
                  <span className="badge badge-emerald" style={{ color: 'var(--accent-cyan)', borderColor: 'rgba(6, 182, 212, 0.2)', backgroundColor: 'rgba(6, 182, 212, 0.1)' }}>
                    目標: {book.target_eps}話
                  </span>
                </div>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.5rem', lineHeight: 1.5, display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: 3, overflow: 'hidden' }}>
                  {book.synopsis || 'あらすじはまだ生成されていません。'}
                </p>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  <span>作成: {new Date(book.created_at).toLocaleDateString()}</span>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteBook(book.id);
                    }}
                  >
                    削除
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
