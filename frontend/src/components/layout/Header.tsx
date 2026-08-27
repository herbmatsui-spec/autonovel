import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { EasyModeDialog } from '@/components/dialogs/EasyModeDialog';
import { SettingsModal } from '@/components/dialogs/SettingsModal';
import type { Book } from '@/types';

interface HeaderProps {
  books: Book[] | null;
  selectedBook: Book | null;
  onSelectBook: (book: Book | null) => void;
  onDeleteBook: (id: number) => void;
  apiKey: string;
  onCreateEasyMode: () => void;
}

export function Header({
  books,
  selectedBook,
  onSelectBook,
  onDeleteBook,
  apiKey,
  onCreateEasyMode,
}: HeaderProps) {
  const navigate = useNavigate();
  const [isEasyModeOpen, setIsEasyModeOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const hasApiKey = Boolean(apiKey && apiKey.trim().length >= 10);

  const handleSelectBook = (book: Book | null) => {
    onSelectBook(book);
    setAnchorEl(null);
    if (book) {
      navigate(`/book/${book.id}`);
    }
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

  return (
    <header className="flex h-[4rem] items-center justify-between px-5 bg-[#0f1117] border-b border-slate-800/80 sticky top-0 z-40">
      {/* Left: Logo & Navigation */}
      <div className="flex items-center space-x-6">
        <button
          onClick={() => navigate('/landing')}
          className="flex items-center space-x-3 text-left group focus:outline-none"
        >
          <div className="h-9 w-9 bg-gradient-to-tr from-indigo-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
            <span className="text-white font-bold text-lg">🎌</span>
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              AutoNovel
              <span className="text-[0.65rem] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-normal">
                v3.6
              </span>
            </h1>
          </div>
        </button>

        {/* Navigation links */}
        <div className="hidden sm:flex items-center space-x-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/landing')}
            className="text-xs text-slate-300 hover:text-white"
          >
            🚀 ホーム
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/books')}
            className="text-xs text-slate-300 hover:text-white"
          >
            📚 作品一覧
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/style-lab')}
            className="text-xs text-indigo-300 hover:text-white hover:bg-indigo-950/40"
          >
            🧪 文体ラボ
          </Button>
        </div>
      </div>

      {/* Right: Actions & Settings */}
      <div className="flex items-center space-x-3">
        {/* Book Selector Dropdown */}
        <div className="relative">
          <Button
            variant="outline"
            size="sm"
            aria-label="本を選択"
            onClick={(e) => setAnchorEl(open ? null : e.currentTarget)}
            className="bg-[#161922] border-slate-700 text-xs text-slate-200 hover:bg-slate-800"
          >
            {selectedBook ? (
              <div className="flex items-center gap-1.5 max-w-[150px]">
                <span className="text-indigo-400 font-mono">#{selectedBook.id}</span>
                <span className="truncate">{selectedBook.title}</span>
              </div>
            ) : (
              <span className="text-slate-400">📖 作品を選択</span>
            )}
            <span className="ml-1.5 text-[0.7rem] text-slate-400">▾</span>
          </Button>

          {open && (
            <div className="absolute right-0 mt-2 w-64 bg-[#161922] rounded-xl border border-slate-700 shadow-2xl z-50 py-1.5 animate-slide-up text-xs">
              <div className="px-3 py-1.5 text-[0.7rem] text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
                最近の作品
              </div>
              <div className="max-h-60 overflow-y-auto">
                {books && books.length > 0 ? (
                  books.map((book) => (
                    <button
                      key={book.id}
                      onClick={() => handleSelectBook(book)}
                      className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-slate-800/80 transition-colors ${
                        selectedBook?.id === book.id ? 'text-indigo-400 font-bold bg-indigo-950/30' : 'text-slate-200'
                      }`}
                    >
                      <span className="truncate flex-1 pr-2">
                        <span className="font-mono text-slate-400 mr-1.5">#{book.id}</span>
                        {book.title}
                      </span>
                      <span className="text-[0.65rem] text-slate-500">{book.genre}</span>
                    </button>
                  ))
                ) : (
                  <p className="px-3 py-3 text-xs text-slate-500 text-center">
                    作成された作品はありません
                  </p>
                )}
              </div>
              {selectedBook && (
                <div className="border-t border-slate-800 p-1.5">
                  <button
                    onClick={() => handleDelete(selectedBook.id)}
                    className="w-full text-left px-2 py-1.5 text-[0.75rem] text-rose-400 hover:bg-rose-950/40 rounded transition-colors"
                  >
                    🗑️ 選択中の本（#{selectedBook.id}）を削除
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Quick New Novel Button */}
        <Button
          variant="default"
          size="sm"
          onClick={handleCreate}
          disabled={!hasApiKey}
          className={`text-xs font-semibold ${
            hasApiKey
              ? 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-md shadow-indigo-500/20'
              : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
          }`}
        >
          ⚡ かんたん作成
        </Button>

        {/* Central Settings Button */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsSettingsOpen(true)}
          className="bg-[#161922] border-slate-700 hover:bg-slate-800 text-slate-200 text-xs flex items-center gap-1.5 px-3"
          title="APIキー・モデル等の全体設定"
        >
          <span className="text-sm">⚙️</span>
          <span className="hidden md:inline font-medium">設定</span>
          {/* Status badge */}
          <span
            className={`w-2 h-2 rounded-full ml-0.5 ${
              hasApiKey ? 'bg-emerald-500 shadow-sm shadow-emerald-500' : 'bg-amber-500 animate-pulse'
            }`}
            title={hasApiKey ? 'API設定完了' : 'APIキー未設定'}
          />
        </Button>
      </div>

      {/* Modals */}
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

      {isSettingsOpen && (
        <SettingsModal
          isOpen={isSettingsOpen}
          onClose={() => setIsSettingsOpen(false)}
        />
      )}
    </header>
  );
}

export default Header;