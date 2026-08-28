import { useState } from 'react';
import { CMDK, useCmdk } from '@cmdk/react';
import { useBookStore } from '@/store/useBookStore';
import { useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';
import { Term } from '@/components/Term';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const { selectedBook, books } = useBookStore((state) => ({
    selectedBook: state.selectedBook,
    books: state.books,
  }));
  const { currentStep } = useWorkspaceStore();
  const [searchQuery, setSearchQuery] = useState('');

  const cmdk = useCmdk();

  // We'll open the command palette when the component mounts and isOpen is true
  // We'll use a useEffect to open the dialog when isOpen changes
  // But note: the CMDK dialog is controlled by the cmdk object.
  // We'll open it when isOpen is true and close it when isOpen is false.
  // We'll use a useEffect to watch isOpen.

  // We'll create a list of items based on the search query.

  // We'll define the items for the command palette.
  const getItems = () => {
    const query = searchQuery.toLowerCase().trim();
    const items: Array<{
      label: string;
      description?: string;
      shortcut?: string[];
      onSelect: () => void;
      // Optional: group and score for sorting
      group?: string;
      score?: number;
    }> = [];

    // Add book items
    if (!query || books.some(b => b.title.toLowerCase().includes(query))) {
      books.forEach((book) => {
        if (!query || book.title.toLowerCase().includes(query)) {
          items.push({
            label: book.title,
            description: `本ID: ${book.id}`,
            shortcut: ['Mod', 'b'],
            onSelect: () => {
              // Navigate to the book's theme step (or last step?)
              // We'll go to the theme step for now.
              if (book.id) {
                navigate(`/book/${book.id}/theme`, { replace: true });
              }
              onClose();
            },
            group: 'books',
            // We can score by exact match or prefix match
            score: query && book.title.toLowerCase().startsWith(query) ? 1 : 0,
          });
        }
      });
    }

    // Add tab items (only if we have a selected book)
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
            label: tab.label,
            description: `現在の書籍: ${selectedBook?.title}、ステップ: ${currentStep}`,
            shortcut: ['Mod', 't'],
            onSelect: () => {
              // Navigate to the tab for the selected book and current step
              if (selectedBook.id && currentStep) {
                navigate(`/book/${selectedBook.id}/${currentStep}/${tab.id}`, { replace: true });
              }
              onClose();
            },
            group: 'tabs',
            score: query && tab.label.toLowerCase().startsWith(query) ? 1 : 0,
          });
        }
      });
    }

    // Sort items by group and then by score (descending) and then by label
    items.sort((a, b) => {
      if (a.group !== b.group) {
        return a.group.localeCompare(b.group);
      }
      if (b.score !== undefined && a.score !== undefined) {
        return b.score - a.score;
      }
      return a.label.localeCompare(b.label);
    });

    return items;
  };

  return (
    <CMDK
      open={isOpen}
      onClose={onClose}
      onInputChange={(e) => setSearchQuery(e.target.value)}
      height={400}
    >
      {(state) => (
        <>
          <CMDK.Input placeholder="コマンドを検索..." />
          <CMDK.Empty>コマンドが見つかりません</CMDK.Empty>
          <CMDK.Items>
            {getItems().map((item, index) => (
              <CMDK.Item
                key={index}
                selected={state.highlightedIndex === index}
                onSelect={() => {
                  item.onSelect();
                  onClose();
                }}
              >
                <CMDK.ItemShortcut>{item.shortcut?.join('+')}</CMDK.ItemShortcut>
                <CMDK.ItemLabel>
                  <Term term={item.label}>{item.label}</Term>
                  {item.description && (
                    <CMDK.ItemDescription>
                      <Term term={item.description}>{item.description}</Term>
                    </CMDK.ItemDescription>
                  )}
                </CMDK.ItemLabel>
              </CMDK.Item>
            ))}
          </CMDK.Items>
          <CMDK.Footer>
            <CMDK.FooterItem>
              <Term term="Escを押して閉じる">Esc to close</Term>
            </CMDK.FooterItem>
          </CMDK.Footer>
        </>
      )}
    </CMDK>
  );
}