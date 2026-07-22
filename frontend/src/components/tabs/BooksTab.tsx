import { Button } from '@/components/ui/button';
import { LoadingState } from '@/components/ui/LoadingState';
import { EmptyState } from '@/components/ui/EmptyState';
import { StatusMessage } from '@/components/ui/StatusMessage';
import type { Book } from '@/types';
import { useBooks } from '@/hooks/useBooks';

interface BooksTabProps {
  selectedBook: Book | null;
  setSelectedBook: (book: Book | null) => void;
  setShowCreateModal: (show: boolean) => void;
}

export function BooksTab({ selectedBook, setSelectedBook, setShowCreateModal }: BooksTabProps) {
  const { books, loading: booksLoading, error: booksError, handleDeleteBook } = useBooks();

  return (
    <div className="animate-fade-in flex flex-col gap-8">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-[1.2rem] text-white font-bold">作成済みの小説一覧</h3>
          <p className="text-[0.85rem] text-[var(--text-secondary)]">現在データベースに保存されている小説の企画及び執筆データです。</p>
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
                className="glass-panel cursor-pointer transition-all"
                onClick={() => setSelectedBook(book)}
                style={{
                  padding: '1.75rem',
                  borderColor: isActive ? 'var(--accent-indigo)' : 'var(--border)',
                  boxShadow: isActive ? 'var(--shadow-glow)' : 'none',
                }}
              >
                <h4 className="text-[1.15rem] text-white font-semibold mb-2">{book.title}</h4>
                <div className="flex gap-2 mb-4">
                  <span className="badge badge-purple">{book.genre}</span>
                  <span className="badge badge-emerald">
                    目標: {book.target_eps}話
                  </span>
                </div>
                <p className="text-sm text-secondary mb-6 line-clamp-3">
                  {book.synopsis || 'あらすじはまだ生成されていません。'}
                </p>

                <div className="flex justify-between items-center text-sm text-muted">
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
