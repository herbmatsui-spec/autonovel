import { Button } from '@/components/ui/button';
import { LoadingState } from '@/components/ui/LoadingState';
import { EmptyState } from '@/components/ui/EmptyState';
import { StatusMessage } from '@/components/ui/StatusMessage';
import { useBooks } from '@/hooks/useBooks';
import { useBookStore } from '@/store/useBookStore';
import { useUIStore } from '@/store/useUIStore';

export default function BooksTab() {
  const { books, loading: booksLoading, error: booksError, handleDeleteBook } = useBooks();
  const { selectedBook, selectBook } = useBookStore();
  const { setCreateModalOpen } = useUIStore();

  return (
    <div className="animate-fade-in flex flex-col gap-8">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">作品一覧</h2>
        <Button
          variant="default"
          onClick={() => setCreateModalOpen(true)}
        >
          新規作成
        </Button>
      </div>

      {booksLoading && <LoadingState message="作品を読み込み中..." />}
      {booksError && <StatusMessage type="error" message="作品の読み込みに失敗しました。" />}
      {books.length === 0 && (
        <EmptyState
          icon="📚"
          title="まだ作品がありません"
          description="「新規作成」ボタンから最初の作品を作成してください。"
        />
      )}
      {!booksLoading && books.length > 0 && (
        <div className="flex flex-col gap-4">
          {books.map((book) => (
            <div
              key={book.id}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  selectBook(book);
                }
              }}
              className={`flex items-center justify-between p-4 rounded-lg border border-[var(--border)] cursor-pointer ${selectedBook?.id === book.id ? 'bg-[var(--accent)]/20' : 'bg-transparent'}`}
              onClick={() => selectBook(book)}
            >
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 bg-[var(--accent)] rounded-flex flex items-center justify-center">
                  <span className="text-white font-bold">#{book.id}</span>
                </div>
                <div>
                  <h3 className="font-semibold">{book.title}</h3>
                  <p className="text-sm text-muted-foreground">
                    {book.genre} • {book.target_eps}話予定 • 作成日: {new Date(book.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    selectBook(book);
                  }}
                >
                  選択
                </Button>
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
          ))}
        </div>
      )}
    </div>
  );
}