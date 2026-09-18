import React from 'react';
import { render, screen, fireEvent, waitFor, renderHook } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { StudioWorkspace } from '../../studio/StudioWorkspace';
import { ZenWritingScreen } from '../ZenWritingScreen';
import { EditorThemeSelector } from '../EditorThemeSelector';
import { RichNovelEditor } from '../RichNovelEditor';
import { AiCoPilotSidebar } from '../AiCoPilotSidebar';
import { InlineDiffSuggestion } from '../InlineDiffSuggestion';
import { ProgressDelight } from '../../common/ProgressDelight';
import { VerticalBookReaderModal } from '../VerticalBookReaderModal';
import { useEditorKeybindings } from '../../../hooks/useEditorKeybindings';
import { useEditorTheme } from '../../../hooks/useEditorTheme';
import { useNovelContext } from '../../../context/NovelContext';
import { WorkspaceLayoutMode } from '../../../types/editorLayout';

// Mock the NovelContext
vi.mock('../../../context/NovelContext', () => ({
  useNovelContext: vi.fn(),
}));

// Mock the EditorThemeSelector hook
vi.mock('../../../hooks/useEditorTheme', () => ({
  useEditorTheme: vi.fn(),
}));

// Mock Tiptap
vi.mock('@tiptap/react', () => ({
  EditorContent: ({ editor, className }: any) => (
    <div className={className} data-testid="tiptap-editor">
      {editor?.getText?.() || ''}
    </div>
  ),
  useEditor: vi.fn((options: any) => {
    let currentText = options?.content || '';
    const mockEditor = {
      getText: () => currentText,
      getHTML: () => `<p>${currentText}</p>`,
      commands: {
        setContent: (t: string) => {
          currentText = t;
          options?.onUpdate?.({ editor: mockEditor });
        },
      },
    };
    return mockEditor;
  }),
}));

// Mock the API client
vi.mock('../api/client', () => ({
  apiFetch: vi.fn(),
  handleResponse: vi.fn(),
}));

// Test wrapper component
const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  return <div>{children}</div>;
};

describe('ZenModeAndEditor Components Tests', () => {
  beforeEach(() => {
    (useNovelContext as any).mockReturnValue({
      character: { name: 'テスト主人公', genre: 'ハイファンタジー (R15)' },
      currentChapterText: 'テスト本文',
      setCurrentChapterText: vi.fn(),
      selectedBookId: '1',
      selectedBook: { title: 'テスト小説' },
      currentEpNum: 1,
      isWizardActive: false,
      setIsWizardActive: vi.fn(),
      wizardStep: 0,
      setWizardStep: vi.fn(),
      hasCompletedWizard: false,
      setHasCompletedWizard: vi.fn(),
      mode: 'studio',
      setMode: vi.fn(),
      lineScores: {},
      setLineScores: vi.fn(),
      chapters: [
        {
          ep_num: 1,
          title: '第1話 テストの旅立ち',
          summary: 'テスト概要',
          content: 'テスト本文',
          is_catharsis: false,
          status: 'draft',
        },
      ],
      setChapters: vi.fn(),
      setCurrentEpNum: vi.fn(),
    });
    (useEditorTheme as any).mockReturnValue({
      theme: 'dark',
      fontFamily: 'serif',
      fontSize: 'medium',
      lineHeight: 'normal',
      showManuscriptGrid: false,
      updateTheme: vi.fn(),
    });
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ reply: 'AIアドバイスです' }),
    }) as any;
  });

  describe('StudioWorkspace Component', () => {
    it('should render studio workspace with default layout', () => {
      render(<StudioWorkspace />, { wrapper: TestWrapper });
      expect(screen.getByTestId('studio-workspace')).toBeInTheDocument();
      expect(screen.getByTestId('studio-tab-bar')).toBeInTheDocument();
    });

    it('should toggle left sidebar visibility', () => {
      render(<StudioWorkspace />, { wrapper: TestWrapper });
      const toggleButton = screen.getByTestId('btn-toggle-left-pane');
      fireEvent.click(toggleButton);
      
      // The sidebar should be collapsed
      expect(screen.getByTestId('left-splitter-collapsed')).toBeInTheDocument();
    });

    it('should switch between layout modes', async () => {
      render(<StudioWorkspace />, { wrapper: TestWrapper });
      
      const zenModeButton = screen.getByTestId('btn-layout-zen');
      fireEvent.click(zenModeButton);
      
      // Should show Zen mode content
      expect(screen.getByTestId('zen-editor-textarea')).toBeInTheDocument();
    });
  });

  describe('ZenWritingScreen Component', () => {
    it('should render zen mode screen when visible', () => {
      const focusState: any = { isZenMode: true };
      render(
        <ZenWritingScreen
          isVisible={true}
          onExit={vi.fn()}
          focusState={focusState}
          onFocusStateChange={vi.fn()}
        />
      );
      
      expect(screen.getByTestId('zen-editor-textarea')).toBeInTheDocument();
      expect(screen.getByText('Zenモード終了 (Esc)')).toBeInTheDocument();
    });

    it('should exit zen mode on Escape key press', () => {
      const focusState: any = { isZenMode: true };
      const onExit = vi.fn();
      
      render(
        <ZenWritingScreen
          isVisible={true}
          onExit={onExit}
          focusState={focusState}
          onFocusStateChange={vi.fn()}
        />
      );
      
      fireEvent.keyDown(document, { key: 'Escape' });
      expect(onExit).toHaveBeenCalled();
    });

    it('should insert ruby when Ctrl+B is pressed', () => {
      const focusState: any = { isZenMode: true };
      const setCurrentChapterText = vi.fn();
      
      (useNovelContext as any).mockReturnValue({
        ...useNovelContext(),
        setCurrentChapterText,
      });
      
      render(
        <ZenWritingScreen
          isVisible={true}
          onExit={vi.fn()}
          focusState={focusState}
          onFocusStateChange={vi.fn()}
        />
      );
      
      const textarea = screen.getByTestId('zen-editor-textarea');
      fireEvent.keyDown(textarea, { ctrlKey: true, key: 'b' });
      
      expect(setCurrentChapterText).toHaveBeenCalled();
    });
  });

  describe('EditorThemeSelector Component', () => {
    it('should display theme options', () => {
      render(<EditorThemeSelector />);
      expect(screen.getByText('🎨 エディタテーマ設定')).toBeInTheDocument();
      expect(screen.getByText('🖤 ダーク')).toBeInTheDocument();
      expect(screen.getByText('📄 ペーパー')).toBeInTheDocument();
      expect(screen.getByText('☕ セピア')).toBeInTheDocument();
      expect(screen.getByText('🤖 サイバーパンク')).toBeInTheDocument();
    });

    it('should change theme when theme button is clicked', () => {
      render(<EditorThemeSelector />);
      
      const paperThemeButton = screen.getByText('📄 ペーパー');
      fireEvent.click(paperThemeButton);
      
      expect(paperThemeButton).toHaveClass('btn-tab--active');
    });

    it('should toggle manuscript grid option', () => {
      render(<EditorThemeSelector />);
      
      const checkbox = screen.getByRole('checkbox', { name: /原稿用紙風のマス目を表示/ });
      fireEvent.click(checkbox);
      
      expect(checkbox).toBeChecked();
    });
  });

  describe('RichNovelEditor Component', () => {
    it('should render Tiptap editor', () => {
      render(<RichNovelEditor initialContent="テストコンテンツ" />);
      expect(screen.getByText('テストコンテンツ')).toBeInTheDocument();
    });

    it('should handle content changes', async () => {
      const onChange = vi.fn();
      const editorRef = React.createRef<any>();
      render(
        <RichNovelEditor
          ref={editorRef}
          initialContent="初期コンテンツ"
          onChange={onChange}
        />
      );
      
      editorRef.current?.setContent('更新されたコンテンツ');
      await waitFor(() => {
        expect(onChange).toHaveBeenCalledWith('更新されたコンテンツ');
      });
    });
  });

  describe('AiCoPilotSidebar Component', () => {
    it('should display AI assistant interface', () => {
      render(
        <AiCoPilotSidebar
          bookId={1}
          currentText="テストテキスト"
        />
      );
      
      expect(screen.getByText('真央（まお）')).toBeInTheDocument();
      expect(screen.getByText('87%')).toBeInTheDocument();
    });

    it('should send and receive messages', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ response: 'AIからの提案です' }),
      }) as any;

      render(
        <AiCoPilotSidebar
          bookId={1}
          currentText="テストテキスト"
        />
      );
      
      const input = screen.getByPlaceholderText('AI編集者に質問または修正を依頼...');
      const sendButton = screen.getByText('📤');
      
      fireEvent.change(input, { target: { value: 'テスト質問' } });
      fireEvent.click(sendButton);
      
      await waitFor(() => {
        expect(screen.getByText('AIからの提案です')).toBeInTheDocument();
      });
    });
  });

  describe('InlineDiffSuggestion Component', () => {
    it('should render with suggestions', () => {
      const suggestions = [
        {
          id: '1',
          originalText: '古いテキスト',
          suggestedText: '新しいテキスト',
          startOffset: 0,
          endOffset: 5,
          type: 'replace' as const,
          status: 'pending' as const,
        },
      ];
      
      render(
        <InlineDiffSuggestion
          suggestions={suggestions}
          content="古いテキストがあります"
          onAccept={vi.fn()}
          onReject={vi.fn()}
        />
      );
      
      expect(screen.getByText('🔍 1件の提案を待機中...')).toBeInTheDocument();
    });

    it('should accept suggestion', () => {
      const suggestions = [
        {
          id: '1',
          originalText: '古いテキスト',
          suggestedText: '新しいテキスト',
          startOffset: 0,
          endOffset: 5,
          type: 'replace' as const,
          status: 'pending' as const,
        },
      ];
      
      const onAccept = vi.fn();
      render(
        <InlineDiffSuggestion
          suggestions={suggestions}
          content="古いテキストがあります"
          onAccept={onAccept}
          onReject={vi.fn()}
        />
      );
      
      const acceptButton = screen.getByTitle('採用');
      fireEvent.click(acceptButton);
      
      expect(onAccept).toHaveBeenCalledWith('1');
    });

    it('should reject suggestion', () => {
      const suggestions = [
        {
          id: '1',
          originalText: '古いテキスト',
          suggestedText: '新しいテキスト',
          startOffset: 0,
          endOffset: 5,
          type: 'replace' as const,
          status: 'pending' as const,
        },
      ];
      
      const onReject = vi.fn();
      render(
        <InlineDiffSuggestion
          suggestions={suggestions}
          content="古いテキストがあります"
          onAccept={vi.fn()}
          onReject={onReject}
        />
      );
      
      const rejectButton = screen.getByTitle('破棄');
      fireEvent.click(rejectButton);
      
      expect(onReject).toHaveBeenCalledWith('1');
    });
  });

  describe('ProgressDelight Component', () => {
    it('should display initial start screen', () => {
      render(
        <ProgressDelight
          isVisible={true}
          onComplete={vi.fn()}
        />
      );
      
      expect(screen.getByText('🎭 生成プロセスを開始')).toBeInTheDocument();
    });

    it('should start generation process when start button is clicked', () => {
      render(
        <ProgressDelight
          isVisible={true}
          onComplete={vi.fn()}
        />
      );
      
      const startButton = screen.getByText('🎭 生成プロセスを開始');
      fireEvent.click(startButton);
      
      expect(screen.getByText('物語があなたのために生まれています...')).toBeInTheDocument();
      expect(screen.getByText('🧠 主人公の心理的葛藤を設計中')).toBeInTheDocument();
      expect(screen.getByText('⚡ 伏線の整合性を過去ログと照合中')).toBeInTheDocument();
    });
  });

  describe('VerticalBookReaderModal Component', () => {
    it('should render book reader modal', () => {
      render(
        <VerticalBookReaderModal
          isOpen={true}
          onClose={vi.fn()}
          content="テスト本の内容です。垂直書き表示で本文が表示されます。"
          bookTitle="テスト小説"
        />
      );
      
      expect(screen.getByText('📖 テスト小説 - 縦書きプレビュー')).toBeInTheDocument();
      expect(screen.getByText('1 / 1')).toBeInTheDocument();
    });

    it('should navigate between pages', async () => {
      render(
        <VerticalBookReaderModal
          isOpen={true}
          onClose={vi.fn()}
          content={'あ'.repeat(500)}
          bookTitle="テスト小説"
        />
      );
      
      expect(screen.getByText('1 / 2')).toBeInTheDocument();
      const nextPageButton = screen.getByText('次のページ →');
      fireEvent.click(nextPageButton);
      
      await waitFor(() => {
        expect(screen.getByText('2 / 2')).toBeInTheDocument();
      });
    });
  });

  describe('useEditorKeybindings Hook', () => {
    it('should handle keybindings correctly', () => {
      const mockOnZenModeToggle = vi.fn();
      const mockOnAiContinue = vi.fn();
      
      const { result } = renderHook(() => useEditorKeybindings({
        onZenModeToggle: mockOnZenModeToggle,
        onAiContinue: mockOnAiContinue,
      }));
      
      expect(result.current.keybindings.zenMode).toBe('F11');
      expect(result.current.keybindings.aiContinue).toBe('Ctrl+Space');
    });

    it('should trigger zen mode toggle on F11 key', () => {
      const mockOnZenModeToggle = vi.fn();
      
      renderHook(() => useEditorKeybindings({
        onZenModeToggle: mockOnZenModeToggle,
      }));
      
      fireEvent.keyDown(document, { key: 'F11' });
      expect(mockOnZenModeToggle).toHaveBeenCalled();
    });
  });
});

// Styles for tests
const testStyles = {
  '.btn-tab--active': {
    backgroundColor: 'rgba(139, 92, 246, 0.2)',
    color: '#c4b5fd',
    border: '1px solid rgba(139, 92, 246, 0.4)',
  },
  '.inline-suggestion-item': {
    backgroundColor: 'rgba(139, 92, 246, 0.2)',
    border: '1px solid var(--accent-purple)',
    animation: 'pulse 2s infinite',
  },
};

const pulseAnimation = {
  '0%, 100%': { opacity: 1 },
  '50%': { opacity: 0.6 },
};