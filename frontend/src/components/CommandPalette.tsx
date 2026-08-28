import { useState, useEffect, useRef } from 'react';
import { useBookStore } from '@/store/useBookStore';
import { useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';
import { Term } from '@/components/Term';
import { recordTransition, NodeId } from '@/lib/usageTracker';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

interface CommandItem {
  label: string;
  description?: string;
  shortcut?: string[];
  onSelect: () => void;
  group?: string;
  score?: number;
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const { selectedBook } = useBookStore();
  const { currentStep } = useWorkspaceStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setSearchQuery('');
      setHighlightedIndex(0);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const query = searchQuery.toLowerCase().trim();
  const items: CommandItem[] = [];

  // If we have selectedBook, add tabs
  if (selectedBook && selectedBook.id) {
    const tabs = [
      { id: 'style-lab', label: '文体ラボ', icon: '🧬' },
      { id: 'plots', label: 'プロット設計', icon: '📖' },
      { id: 'analytics', label: '品質＆販促', icon: '📈' },
      { id: 'audit', label: '品質監査', icon: '⚖️' },
      { id: 'monitor', label: '進捗モニター', icon: '📡' },
      { id: 'strategy', label: '戦略分析', icon: '📈' },
      { id: 'import', label: 'インポート', icon: '📥' },
    ];

    tabs.forEach((tab) => {
      if (!query || tab.label.toLowerCase().includes(query)) {
        items.push({
          label: `${tab.icon} ${tab.label}`,
          description: `現在の書籍: ${selectedBook.title}、ステップ: ${currentStep || 'theme'}`,
          shortcut: ['Tab', tab.id],
          onSelect: () => {
            if (selectedBook.id) {
              const step = currentStep || 'theme';
              navigate(`/book/${selectedBook.id}/${step}/${tab.id}`, { replace: true });
              const fromNode: NodeId = `step-${step}`;
              const toNode: NodeId = `tab-${tab.id}`;
              recordTransition(fromNode, toNode);
            }
          },
          group: 'tabs',
          score: query && tab.label.toLowerCase().startsWith(query) ? 1 : 0,
        });
      }
    });
  }

  // Add Step items
  const steps = [
    { id: 'theme', label: 'テーマ設定', icon: '🎯' },
    { id: 'outline', label: 'あらすじ作成', icon: '📖' },
    { id: 'write', label: '本文執筆', icon: '✍️' },
    { id: 'finish', label: '仕上げ・監査', icon: '✨' },
    { id: 'publish', label: '作品公開', icon: '🚀' },
  ];

  if (selectedBook && selectedBook.id) {
    steps.forEach((step) => {
      if (!query || step.label.toLowerCase().includes(query)) {
        items.push({
          label: `${step.icon} ${step.label}`,
          description: `ステップへ移動: ${step.label}`,
          shortcut: ['Step'],
          onSelect: () => {
            if (selectedBook.id) {
              navigate(`/book/${selectedBook.id}/${step.id}`, { replace: true });
            }
          },
          group: 'steps',
          score: query && step.label.toLowerCase().startsWith(query) ? 1 : 0,
        });
      }
    });
  }

  items.sort((a, b) => {
    if ((a.group || '') !== (b.group || '')) {
      return (a.group || '').localeCompare(b.group || '');
    }
    if (b.score !== undefined && a.score !== undefined && b.score !== a.score) {
      return b.score - a.score;
    }
    return a.label.localeCompare(b.label);
  });

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex((prev) => (items.length ? (prev + 1) % items.length : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex((prev) => (items.length ? (prev - 1 + items.length) % items.length : 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (items[highlightedIndex]) {
        items[highlightedIndex].onSelect();
        onClose();
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div 
        className="w-full max-w-lg overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--bg-card,#1e1e2e)] text-[var(--text-primary,#fff)] shadow-2xl animate-fade-in"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <div className="p-3 border-b border-[var(--border)]">
          <input
            ref={inputRef}
            type="text"
            className="w-full bg-transparent px-3 py-2 text-sm outline-none placeholder:text-[var(--text-muted,#888)]"
            placeholder="コマンドを検索..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setHighlightedIndex(0);
            }}
          />
        </div>
        <div className="max-h-80 overflow-y-auto p-2">
          {items.length === 0 ? (
            <div className="p-4 text-center text-sm text-[var(--text-muted,#888)]">コマンドが見つかりません</div>
          ) : (
            items.map((item, idx) => (
              <div
                key={idx}
                className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors ${
                  highlightedIndex === idx ? 'bg-[var(--accent,#6366f1)]/20 text-[var(--accent,#6366f1)] font-medium' : 'hover:bg-[var(--bg-muted,#2a2a3c)]'
                }`}
                onMouseEnter={() => setHighlightedIndex(idx)}
                onClick={() => {
                  item.onSelect();
                  onClose();
                }}
              >
                <div>
                  <Term term={item.label}>{item.label}</Term>
                  {item.description && (
                    <div className="text-xs text-[var(--text-secondary,#aaa)] mt-0.5">{item.description}</div>
                  )}
                </div>
                {item.shortcut && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-[var(--bg-muted,#333)] text-[var(--text-secondary,#aaa)]">
                    {item.shortcut.join('+')}
                  </span>
                )}
              </div>
            ))
          )}
        </div>
        <div className="px-4 py-2 border-t border-[var(--border)] text-xs text-[var(--text-muted,#888)] flex justify-between">
          <span>↑↓ で選択 / Enter で実行</span>
          <span>Esc で閉じる</span>
        </div>
      </div>
    </div>
  );
}