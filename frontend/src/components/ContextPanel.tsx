import { useNavigate } from 'react-router-dom';
import { useBookStore } from '@/store/useBookStore';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';
import { Term } from '@/components/Term';

interface ContextPanelProps {
  // We might pass in the bookId and currentStep, but we'll get them from stores
}

export default function ContextPanel() {
  const navigate = useNavigate();
  const { selectedBook } = useBookStore();
  const { currentStep } = useWorkspaceStore();
  
  // If no book is selected, we show a message or hide the panel
  if (!selectedBook) {
    return null;
  }

  // Define shortcuts for each step
  const stepShortcuts: Record<string, Array<{
    label: string;
    icon: string;
    description: string;
    shortcut: string[]; // e.g., ['Mod', 's']
    onClick: () => void;
  }>> = {
    theme: [
      {
        label: 'スタイルラボで参照',
        icon: '🧬',
        description: '現在のテーマをスタイルラボで分析',
        shortcut: ['Mod', 's'],
        onClick: () => {
          if (selectedBook?.id) {
            navigate(`/book/${selectedBook.id}/theme/style-lab`, { replace: true });
          }
        }
      },
      {
        label: '市場分析を確認',
        icon: '📈',
        description: '現在のジャンルの市場動向を分析',
        shortcut: ['Mod', 'a'],
        onClick: () => {
          if (selectedBook?.id) {
            navigate(`/book/${selectedBook.id}/theme/analytics`, { replace: true });
          }
        }
      }
    ],
    outline: [
      {
        label: 'プロットを確認',
        icon: '📖',
        description: '現在のアウトラインをプロットビューで確認',
        shortcut: ['Mod', 'p'],
        onClick: () => {
          if (selectedBook?.id) {
            navigate(`/book/${selectedBook.id}/outline/plots`, { replace: true });
          }
        }
      },
      {
        label: 'キャラクターを編集',
        icon: '👥',
        description: 'キャラクター詳細を編集',
        shortcut: ['Mod', 'c'],
        onClick: () => {
          if (selectedBook?.id) {
            // We'll navigate to the books tab and hope it shows the character list? We'll need to fix this later.
            // For now, we'll go to the books tab.
            navigate(`/books`, { replace: true });
          }
        }
      }
    ],
    write: [
      {
        label: 'スタイルラボでチェック',
        icon: '🧬',
        description: '現在の章をスタイルラボで分析',
        shortcut: ['Mod', 's'],
        onClick: () => {
          if (selectedBook?.id) {
            navigate(`/book/${selectedBook.id}/write/style-lab`, { replace: true });
          }
        }
      },
      {
        label: 'プロットを確認',
        icon: '📖',
        description: '現在の章のプロット整合性を確認',
        shortcut: ['Mod', 'p'],
        onClick: () => {
          if (selectedBook?.id) {
            navigate(`/book/${selectedBook.id}/write/plots`, { replace: true });
          }
        }
      }
    ],
    finish: [
      {
        label: 'スタイルラボで最終チェック',
        icon: '🧬',
        description: '仕上げ前のスタイルチェック',
        shortcut: ['Mod', 's'],
        onClick: () => {
          if (selectedBook?.id) {
            navigate(`/book/${selectedBook.id}/finish/style-lab`, { replace: true });
          }
        }
      },
      {
        label: '品質監査を実行',
        icon: '⚖️',
        description: '仕上げ後の品質監査を実行',
        shortcut: ['Mod', 'u'],
        onClick: () => {
          if (selectedBook?.id) {
            navigate(`/book/${selectedBook.id}/finish/audit`, { replace: true });
          }
        }
      }
    ],
    publish: [
      {
        label: 'スタイルラボで最終確認',
        icon: '🧬',
        description: '公開前の最終スタイルチェック',
        shortcut: ['Mod', 's'],
        onClick: () => {
          if (selectedBook?.id) {
            navigate(`/book/${selectedBook.id}/publish/style-lab`, { replace: true });
          }
        }
      },
      {
        label: '配信チャネルを設定',
        icon: '⚙️',
        description: '公開先のチャネルを設定',
        shortcut: ['Mod', 'd'],
        onClick: () => {
          if (selectedBook?.id) {
            navigate(`/book/${selectedBook.id}/publish/analytics`, { replace: true }); // Using analytics for now
          }
        }
      }
    ],
  };

  // Get shortcuts for the current step
  const shortcuts = stepShortcuts[currentStep || 'theme'] || [];

  return (
    <div className="fixed bottom-0 left-0 right-0 h-16 bg-[var(--bg-muted)] border-t border-[var(--border)] px-4 py-2 flex flex-wrap gap-4 items-center sm:hidden">
      {/* Hidden on small screens, we'll show on medium and up */}
      <div className="hidden sm:flex sm:flex-wrap sm:gap-4 sm:items-center">
        <div className="flex flex-col items-center">
          <div className="text-xs text-[var(--text-secondary)]">ショートカット</div>
          {shortcuts.map((shortcut, index) => (
            <div key={index} className="flex items-center space-x-2 mt-2">
              <span className="text-[var(--accent)]">{shortcut.icon}</span>
              <div className="text-xs space-y-1">
                <Term term={shortcut.label}>{shortcut.label}</Term>
                <Term term={shortcut.description} className="text-[var(--text-secondary)]">{shortcut.description}</Term>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}