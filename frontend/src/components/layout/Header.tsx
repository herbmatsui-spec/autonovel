import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { useBookStore } from '@/store/useBookStore';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';
import { useUIStore } from '@/store/useUIStore';
import { toast } from 'sonner';
import { EasyModeDialog } from '@/components/dialogs/EasyModeDialog';
import type { Book } from '@/types';

interface HeaderProps {
  books: Book[] | null;
  selectedBook: Book | null;
  onSelectBook: (book: Book | null) => void;
  onDeleteBook: (id: number) => void;
  apiKey: string;
  setApiKey: (key: string) => void;
  modelType: string;
  setModelType: (type: string) => void;
  isExpertMode: boolean;
  setIsExpertMode: (bool: boolean) => void;
  isFirstRun: boolean;
  onCreateEasyMode: () => void;
}

export default function Header({
  books,
  selectedBook,
  onSelectBook,
  onDeleteBook,
  apiKey,
  setApiKey,
  modelType,
  setModelType,
  isExpertMode,
  setIsExpertMode,
  isFirstRun,
  onCreateEasyMode,
}: HeaderProps) {
  const navigate = useNavigate();
  const [isEasyModeOpen, setIsEasyModeOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);
  const { setCreateModalOpen } = useUIStore();

  // Redirect to setup if first run and not already on setup
  useEffect(() => {
    if (isFirstRun && window.location.pathname !== '/setup') {
      navigate('/setup', { replace: true });
    }
  }, [isFirstRun, navigate, window.location.pathname]);

  const handleSelectBook = (book: Book | null) => {
    onSelectBook(book);
    setAnchorEl(null);
  };

  const handleDelete = (id: number) => {
    onDeleteBook(id);
    if (selectedBook?.id === id) {
      onSelectBook(null);
    }
    setAnchorEl(null);
  };

  const handleCreate = () => {
    setIsEasyModeOpen(true);
    setAnchorEl(null);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  return (
    <header className="flex h-[4rem] items-center justify-between px-4 bg-[var(--bg-sidebar)] border-b border-[var(--border)]">
      <div className="flex items-center space-x-3">
        <div className="h-8 w-8 bg-[var(--accent)] rounded-full flex items-center justify-center">
          <span className="text-white font-bold">🎌</span>
        </div>
        <h1 className="text-xl font-bold">AutoNovel</h1>
      </div>

      <div className="flex items-center space-x-4">
        {/* 本を選ぶ dropdown */}
        <div className="relative">
          <Button
            variant="outline"
            aria-label="本を選択"
            onClick={(e) => setAnchorEl(e.currentTarget)}
          >
            {selectedBook ? (
              <>
                <span className="mr-2">#{selectedBook.id}</span>
                <span className="truncate max-w-[120px]">{selectedBook.title}</span>
              </>
            ) : (
              <span className="text-muted-foreground">本を選択</span>
            )}
            <span className="ml-2 text-xs">▾</span>
          </Button>
          {/* Dropdown menu */}
          {open && (
            <div className="absolute right-0 mt-2 w-56 bg-white rounded border shadow-lg z-20 py-1">
              {books?.map((book) => (
                <button
                  key={book.id}
                  onClick={() => handleSelectBook(book)}
                  className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100`}
                >
                  #{book.id} {book.title}
                </button>
              ))}
              {!books || books.length === 0 ? (
                <p className="px-4 py-2 text-sm text-muted-foreground">
                  本がありません
                </p>
              ) : null}
              <div className="border-t px-4 py-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    if (selectedBook) {
                      handleDelete(selectedBook.id);
                    }
                  }}
                  className="w-full text-left text-sm text-destructive"
                >
                  選択中の本を削除
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* API Key */}
        <div className="flex items-center space-x-2">
          <label className="text-xs text-muted-foreground">API Key:</label>
          <Input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk-..."
            className="w-[200px]"
          />
        </div>

        {/* Model Type */}
        <div className="flex items-center space-x-2">
          <label className="text-xs text-muted-foreground">Model:</label>
          <Button
            variant="ghost"
            onClick={() => setModelType(modelType === 'openai' ? 'gemini' : 'openai')}
          >
            <span className="hidden md:inline">{modelType === 'openai' ? 'OpenAI' : 'Gemini'}</span>
          </Button>
        </div>

        {/* Expert Mode */}
        <div className="flex items-center space-x-2">
          <label className="text-xs text-muted-foreground">Expert:</label>
          <Button
            variant="ghost"
            onClick={() => setIsExpertMode(!isExpertMode)}
          >
            <span>{isExpertMode ? 'ON' : 'OFF'}</span>
          </Button>
        </div>

        {/* 新規作成 (かんたんモード) */}
        <Button
          variant="default"
          onClick={handleCreate}
          disabled={!apiKey || apiKey.length < 10}
        >
          {apiKey && apiKey.length >= 10 ? '⚡ かんたんモード' : 'APIキーが必要'}
        </Button>
      </div>

      {/* EasyModeDialog as modal */}
      {isEasyModeOpen && (
        <EasyModeDialog
          isOpen={isEasyModeOpen}
          onClose={() => setIsEasyModeOpen(false)}
          onSubmit={() => {
            onCreateEasyMode();
            setIsEasyModeOpen(false);
          }}
        />
      )}
    </header>
  );
}