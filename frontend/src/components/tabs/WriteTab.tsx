import { Chapter } from '@/types';
import { EmptyState } from '@/components/ui/EmptyState';
import { WritingForm } from '../write/WritingForm';
import { ImportForm } from '../write/ImportForm';
import { BiblePanel } from '../write/BiblePanel';
import { ChapterCard } from '../write/ChapterCard';
import { useWritingStore } from '@/store/useWritingStore';
import { useBookStore } from '@/store/useBookStore';
import { useAppActions } from '@/hooks/useAppActions';
import { useTaskStore } from '@/store/useTaskStore';
import { Button } from '@/components/ui/button';

export function WriteTab() {
  const { chapters, bible } = useBookStore();
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
    genre,
    setGenre,
    title,
    setTitle,
    wordCount,
    setWordCount,
    platform,
    setPlatform,
    showPreview,
    setShowPreview,
  } = useWritingStore();
  const { handleTriggerWriting, handleRefineErotic, handleImportChapter } = useAppActions(() => {});
  const { activeTaskId } = useTaskStore();

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
            <EmptyState
              icon="📖"
              title="まだ章がありません"
              description="「執筆を開始」ボタンから最初の章を執筆してください。"
            />
          ) : (
            <>
              {/** Pagination */ }
              <div className="flex flex-wrap items-center gap-2 mb-4">
                <span className="text-sm">表示範囲:</span>
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
                  .map((chapter: Chapter) => (
                    <ChapterCard key={chapter.ep_num} chapter={chapter} />
                  ))}
              </div>
            </>
          )}
        </div>

        <div className="pt-4 border-t border-[var(--border)]">
          <h2 className="text-xl font-bold mb-4">執筆コントロール</h2>
          <WritingForm
            writeFrom={writeFrom}
            setWriteFrom={setWriteFrom}
            writeTo={writeTo}
            setWriteTo={setWriteTo}
            writePassion={writePassion}
            setWritePassion={setWritePassion}
            onSubmit={handleTriggerWriting}
            onRefineErotic={handleRefineErotic}
            disabled={!!activeTaskId}
            genre={genre}
            setGenre={setGenre}
            title={title}
            setTitle={setTitle}
            wordCount={wordCount}
            setWordCount={setWordCount}
            platform={platform}
            setPlatform={setPlatform}
          />
        </div>
      </div>

      {/* Right Column: Bible & Import */}
      <div className="flex flex-col gap-[2rem]">
        <BiblePanel bible={bible} />
        <ImportForm
          importEpNum={importEpNum}
          setImportEpNum={setImportEpNum}
          importText={importText}
          setImportText={setImportText}
          importDoRefine={importDoRefine}
          setImportDoRefine={setImportDoRefine}
          onSubmit={handleImportChapter}
          disabled={!!activeTaskId}
          showPreview={showPreview}
          setShowPreview={setShowPreview}
        />
      </div>
    </div>
  );
}

export default WriteTab;