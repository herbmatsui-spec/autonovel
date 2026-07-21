import { Book, Chapter, Bible } from '@/types';
import { EmptyState } from '@/components/ui/EmptyState';
import { StatusMessage } from '@/components/ui/StatusMessage';
import { WritingForm } from '../write/WritingForm';
import { ImportForm } from '../write/ImportForm';
import { BiblePanel } from '../write/BiblePanel';
import { ChapterCard } from '../write/ChapterCard';
import { usePagination } from '@/hooks/usePagination';
import { useWritingStore } from '@/store/useWritingStore';

interface WriteTabProps {
  selectedBook: Book;
  chapters: Chapter[];
  bible: Bible | null;
  writeFrom: number;
  setWriteFrom: (val: number) => void;
  writeTo: number;
  setWriteTo: (val: number) => void;
  writePassion: number;
  setWritePassion: (val: number) => void;
  handleTriggerWriting: () => void;
  importEpNum: number;
  setImportEpNum: (val: number) => void;
  importText: string;
  setImportText: (val: string) => void;
  importDoRefine: boolean;
  setImportDoRefine: (val: boolean) => void;
  handleImportChapter: (e: React.FormEvent) => void;
  activeTaskId: string | null;
  genre: string;
  setGenre: (val: string) => void;
  title: string;
  setTitle: (val: string) => void;
  wordCount: number;
  setWordCount: (val: number) => void;
  platform: string;
  setPlatform: (val: string) => void;
  showPreview: boolean;
  setShowPreview: (val: boolean) => void;
}

export function WriteTab({
  chapters,
  bible,
  writeFrom,
  setWriteFrom,
  writeTo,
  setWriteTo,
  writePassion,
  setWritePassion,
  handleTriggerWriting,
  importEpNum,
  setImportEpNum,
  importText,
  setImportText,
  importDoRefine,
  setImportDoRefine,
  handleImportChapter,
  activeTaskId,
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
}: WriteTabProps) {
  const { error, clearError } = useWritingStore();
  const { page, setPage, totalPages, paginatedItems } = usePagination(chapters.length, 5);

  return (
    <div className="animate-fade-in grid grid-cols-1 lg:grid-cols-3 gap-6">
      {error && (
        <div className="glass-panel p-4" style={{ borderColor: 'var(--accent-red)' }}>
          <StatusMessage type="error" message={error} onClose={clearError} />
        </div>
      )}
      <div className="flex flex-col gap-8 lg:col-span-2">
        <WritingForm
          writeFrom={writeFrom}
          setWriteFrom={setWriteFrom}
          writeTo={writeTo}
          setWriteTo={setWriteTo}
          writePassion={writePassion}
          setWritePassion={setWritePassion}
          onSubmit={handleTriggerWriting}
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

        <div>
          <h3 style={{ fontSize: '1.2rem', marginBottom: '1rem', color: '#fff' }}>
            📖 執筆完了エピソード
          </h3>
          {chapters.length === 0 ? (
            <EmptyState
              icon="📖"
              title="まだ執筆されたチャプターがありません"
              description="上のフォームから自動執筆を開始してください。"
            />
          ) : (
            <>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                {paginatedItems(chapters).map((ch) => (
                  <ChapterCard key={ch.ep_num} chapter={ch} qualityScore={ch.quality_score} killerPhrase={ch.killer_phrase} />
                ))}
              </div>
              {totalPages > 1 && (
                <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', marginTop: '1rem', alignItems: 'center' }}>
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="btn btn-secondary"
                  >
                    ← 前
                  </button>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    ページ {page} / {totalPages} （{chapters.length}話中）
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="btn btn-secondary"
                  >
                    次 →
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-6">
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
