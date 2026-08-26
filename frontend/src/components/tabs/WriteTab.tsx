import { Book, Chapter, Bible } from '@/types';
import { EmptyState } from '@/components/ui/EmptyState';
import { StatusMessage } from '@/components/ui/StatusMessage';
import { WritingForm } from '../write/WritingForm';
import { ImportForm } from '../write/ImportForm';
import { BiblePanel } from '../write/BiblePanel';
import { ChapterCard } from '../write/ChapterCard';
import { usePagination } from '@/hooks/usePagination';
import { useWritingStore } from '@/store/useWritingStore';
import { useBookStore } from '@/store/useBookStore';
import { useAppActions } from '@/hooks/useAppActions';
import { useTaskStore } from '@/store/useTaskStore';
import { Button } from '@/components/ui/button';

export default function WriteTab() {
  const { selectedBook, chapters, bible } = useBookStore();
  const {
    writeFrom,
    setWriteFrom,
    writeTo,
    setWriteTo,
    writePassion,
    setWritePassion,
    importEpNum,
    setImportEpNum,
    importText,
    setImportText,
    importDoRefine,
    setImportDoRefine,
  } = useWritingStore();
  const { handleTriggerWriting, handleRefineErotic, handleImportChapter } = useAppActions((_) => {});
  const { activeTaskId } = useTaskStore();
  const { error, clearError } = useWritingStore();
  const { page, setPage, totalPages, paginatedItems } = usePagination<Chapter>(chapters.length, 5);

  return (
    <div className="animate-fade-in grid grid-cols-[1fr_350px] gap-[2rem]">
      {/* Left Column: Chapters browse & controls */}
      <div className="flex flex-col gap-[2rem]">
        <div className="flex flex-col gap-4">
          <h2 className="text-xl font-bold">章一覧</h2>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => setWriteFrom(1)}
              disabled={writeFrom <= 1}
            >
              第一話から
            </Button>
            <Button
              variant="outline"
              onClick={() => setWriteTo(chapters.length)}
              disabled={writeTo >= chapters.length || chapters.length === 0}
            >
              最終話まで
            </Button>
          </div>
          {chapters.length === 0 ? (
            <EmptyState>
              <h3 className="font-semibold">まだ章がありません</h3>
              <p className="text-sm text-muted-foreground">
                「執筆を開始」ボタンから最初の章を執筆してください。
              </p>
            </EmptyState>
          ) : (
            <>
              {/** Pagination */ }
              <div className="flex flex-wrap items-center gap-2 mb-4">
                <label className="text-sm">表示範囲:</label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setWriteFrom(Math.max(1, writeFrom - 5))}
                  disabled={writeFrom <= 1}
                >
                  ‹‹
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setWriteFrom(Math.max(1, writeFrom - 1))}
                  disabled={writeFrom <= 1}
                >
                  ‹
                </Button>
                <span className="text-xs nx">
                  {writeFrom} ～ {Math.min(writeTo, chapters.length)} / {chapters.length} 話
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setWriteTo(Math.min(chapters.length, writeTo + 1))}
                  disabled={writeTo >= chapters.length}
                >
                  ›
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setWriteTo(Math.min(chapters.length, writeTo + 5))}
                  disabled={writeTo >= chapters.length}
                >
                  ››
                </Button>
              </div>
              {/* Chapter list */ }
              <div className="space-y-2">
                {chapters
                  .slice(writeFrom - 1, writeTo)
                  .map((chapter) => (
                    <ChapterCard key={chapter.id} chapter={chapter} />
                  ))}
              </div>
            </>
          )}
        </div>

        <div className="pt-4 border-t border-[var(--border)]">
          <h2 className="text-xl font-bold mb-4">執筆コントロール</h2>
          <WritingForm
            book={selectedBook}
            activeTaskId={activeTaskId}
          />
        </div>
      </div>

      {/* Right Column: Bible & Import */}
      <div className="flex flex-col gap-[2rem]">
        <BiblePanel bible={bible} />
        <ImportForm
          activeTaskId={activeTaskId}
          onImportChapter={handleImportChapter}
        />
      </div>
    </div>
  );
}