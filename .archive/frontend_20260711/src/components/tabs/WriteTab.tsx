import React from 'react';
import { Book, Chapter, Bible } from '../types';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { StatusMessage } from '@/components/ui/StatusMessage';
import { WritingForm } from '../write/WritingForm';
import { ImportForm } from '../write/ImportForm';
import { BiblePanel } from '../write/BiblePanel';
import { ChapterCard } from '../write/ChapterCard';

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
}: WriteTabProps) {
  return (
    <div className="animate-fade-in grid grid-cols-1 lg:grid-cols-3 gap-6">
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
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {chapters.map((ch) => (
                <ChapterCard key={ch.ep_num} chapter={ch} />
              ))}
            </div>
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
        />
      </div>
    </div>
  );
}
