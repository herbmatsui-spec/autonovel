import { useEffect, useRef } from 'react';
import { useNovelContext } from '../context/NovelContext';

interface EditorKeybindings {
  zenMode: string;
  aiContinue: string;
  aiProofread: string;
  toggleTheme: string;
  toggleManuscriptGrid: string;
}

interface UseEditorKeybindingsProps {
  onZenModeToggle?: () => void;
  onAiContinue?: () => void;
  onAiProofread?: () => void;
  onToggleTheme?: () => void;
  onToggleManuscriptGrid?: () => void;
  isZenMode?: boolean;
}

export const useEditorKeybindings = ({
  onZenModeToggle,
  onAiContinue,
  onAiProofread,
  onToggleTheme,
  onToggleManuscriptGrid,
  isZenMode = false,
}: UseEditorKeybindingsProps) => {
  const {
    setMode,
    mode,
  } = useNovelContext();

  const keybindings: EditorKeybindings = {
    zenMode: 'F11',
    aiContinue: 'Ctrl+Space',
    aiProofread: 'Ctrl+Enter',
    toggleTheme: 'Ctrl+Shift+T',
    toggleManuscriptGrid: 'Ctrl+Shift+G',
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    // Prevent default browser behavior for our shortcuts
    if (isModifierKey(event)) {
      return;
    }

    // Check for Zen Mode toggle (F11 or Ctrl+B)
    if (event.key === 'F11' || (event.ctrlKey || event.metaKey) && event.key === 'b') {
      event.preventDefault();
      onZenModeToggle?.();
    }
    // Check for AI Continue (Ctrl+Space)
    else if ((event.ctrlKey || event.metaKey) && event.key === ' ') {
      event.preventDefault();
      onAiContinue?.();
    }
    // Check for AI Proofread (Ctrl+Enter)
    else if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      onAiProofread?.();
    }
    // Check for Toggle Theme (Ctrl+Shift+T)
    else if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 't') {
      event.preventDefault();
      onToggleTheme?.();
    }
    // Check for Toggle Manuscript Grid (Ctrl+Shift+G)
    else if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'g') {
      event.preventDefault();
      onToggleManuscriptGrid?.();
    }
    // Check for Easy Mode toggle (Ctrl+Shift+E)
    else if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'e') {
      event.preventDefault();
      if (mode !== 'easy') {
        setMode('easy');
      }
    }
  };

  const isModifierKey = (event: KeyboardEvent): boolean => {
    return event.key === 'Control' || event.key === 'Meta' ||
           event.key === 'Shift' || event.key === 'Alt';
  };

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [onZenModeToggle, onAiContinue, onAiProofread, onToggleTheme, onToggleManuscriptGrid, mode]);

  // Mobile device support - show touch-friendly version of keybindings
  const getMobileKeybindings = () => {
    return {
      zenMode: '📖 集中',
      aiContinue: '💭 続き',
      aiProofread: '🔍 校正',
      toggleTheme: '🎨 テーマ',
      toggleManuscriptGrid: '📄 マス目',
    };
  };

  return {
    keybindings,
    getMobileKeybindings,
  };
};