import React, { useState, useEffect, useRef } from "react";
import { useNovelContext } from "../../context/NovelContext";
import { EditorFocusState, ZenModeConfig } from "../../types/editorLayout";
import { useEditorTheme } from "../../hooks/useEditorTheme";

interface ZenWritingScreenProps {
  isVisible: boolean;
  onExit: () => void;
  focusState: EditorFocusState;
  onFocusStateChange: (state: Partial<EditorFocusState>) => void;
}

export const ZenWritingScreen: React.FC<ZenWritingScreenProps> = ({
  isVisible,
  onExit,
  focusState,
  onFocusStateChange,
}) => {
  const {
    character,
    currentChapterText,
    setCurrentChapterText,
    selectedBook,
    currentEpNum,
  } = useNovelContext();
  
  const {
    theme,
    fontFamily,
    fontSize,
    lineHeight,
    showManuscriptGrid,
  } = useEditorTheme();

  const [wordCount, setWordCount] = useState(0);
  const [targetWordCount] = useState(3000);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [showCursor, setShowCursor] = useState(true);
  const [lastActivity, setLastActivity] = useState(Date.now());
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const cursorBlinkRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (!isVisible) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onExit();
      }
      
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case 's':
            e.preventDefault();
            break;
          case 'b':
            e.preventDefault();
            handleInsertRuby();
            break;
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isVisible, onExit]);

  useEffect(() => {
    if (!isVisible) {
      if (cursorBlinkRef.current) {
        clearInterval(cursorBlinkRef.current);
      }
      setShowCursor(true);
      return;
    }

    const updateCursorVisibility = () => {
      const now = Date.now();
      const inactiveTime = now - lastActivity;
      
      if (inactiveTime > 2000) {
        setShowCursor(false);
      } else {
        setShowCursor(true);
        if (cursorBlinkRef.current) {
          clearInterval(cursorBlinkRef.current);
        }
        cursorBlinkRef.current = setInterval(() => {
          setShowCursor(prev => !prev);
        }, 500);
      }
    };

    const handleActivity = () => {
      setLastActivity(Date.now());
      setShowCursor(true);
    };

    const events = ['mousedown', 'keydown', 'scroll', 'touchstart'];
    events.forEach(event => {
      document.addEventListener(event, handleActivity, { passive: true });
    });

    const activityInterval = setInterval(updateCursorVisibility, 100);

    return () => {
      if (cursorBlinkRef.current) {
        clearInterval(cursorBlinkRef.current);
      }
      events.forEach(event => {
        document.removeEventListener(event, handleActivity);
      });
      clearInterval(activityInterval);
    };
  }, [isVisible, lastActivity]);

  useEffect(() => {
    setWordCount(currentChapterText.replace(/\s/g, '').length);
  }, [currentChapterText]);

  const handleInsertRuby = () => {
    if (!textareaRef.current) return;
    const start = textareaRef.current.selectionStart;
    const end = textareaRef.current.selectionEnd;
    const selected = currentChapterText.substring(start, end) || "親文字";
    const rubySnippet = `｜${selected}《ルビ》`;
    const before = currentChapterText.substring(0, start);
    const after = currentChapterText.substring(end);
    const updated = `${before}${rubySnippet}${after}`;
    setCurrentChapterText(updated);

    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        const cursorStart = start + 1 + selected.length + 1;
        textareaRef.current.setSelectionRange(cursorStart, cursorStart + 2);
      }
    }, 50);
  };

  const getProgressPercentage = () => {
    return Math.min((wordCount / targetWordCount) * 100, 100);
  };

  if (!isVisible) return null;

  const getThemeClasses = () => {
    const baseClasses = "zen-mode-container";
    
    if (theme === 'paper') {
      return `${baseClasses} theme-paper`;
    } else if (theme === 'sepia') {
      return `${baseClasses} theme-sepia`;
    } else if (theme === 'cyberpunk') {
      return `${baseClasses} theme-cyberpunk`;
    } else {
      return `${baseClasses} theme-dark`;
    }
  };

  const getFontClasses = () => {
    switch (fontFamily) {
      case 'serif':
        return 'font-serif';
      case 'sans':
        return 'font-sans';
      case 'mincho':
        return 'font-mincho';
      default:
        return 'font-serif';
    }
  };

  const getManuscriptGridStyle = () => {
    if (!showManuscriptGrid) return {};
    
    return {
      backgroundImage: 'linear-gradient(to bottom, transparent 0%, rgba(139, 92, 246, 0.1) 50%, transparent 100%)',
      backgroundSize: '100% 40px',
      backgroundRepeat: 'repeat-y'
    };
  };

  return (
    <div className={getThemeClasses()} style={getManuscriptGridStyle()}>
      <div className="zen-mode__header">
        <span className="zen-mode__title">{selectedBook?.title || "小説"}</span>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <span className="zen-mode__manuscript">
            📄 約{Math.ceil(wordCount / 400)}枚 ({wordCount}/{targetWordCount}字)
          </span>
          <div className="progress-bar-container" style={{ width: "200px", height: "8px", backgroundColor: "rgba(255,255,255,0.1)", borderRadius: "4px", overflow: "hidden" }}>
            <div 
              style={{ 
                width: `${getProgressPercentage()}%`, 
                height: "100%", 
                backgroundColor: wordCount >= targetWordCount ? "#10b981" : "#8b5cf6",
                transition: "width 0.3s ease"
              }}
            />
          </div>
          <button
            type="button"
            className="zen-mode__exit"
            onClick={onExit}
            aria-label="Zenモードを終了"
          >
            Zenモード終了 (Esc)
          </button>
        </div>
      </div>

      <textarea
        ref={textareaRef}
        data-testid="zen-editor-textarea"
        className={`${getFontClasses()} zen-mode-textarea ${fontSize === 'small' ? 'text-sm' : fontSize === 'large' ? 'text-lg' : fontSize === 'huge' ? 'text-xl' : 'text-base'} ${lineHeight === 'tight' ? 'leading-tight' : lineHeight === 'normal' ? 'leading-normal' : lineHeight === 'relaxed' ? 'leading-relaxed' : 'leading-loose'}`}
        style={{
          fontFamily: 'inherit',
          flex: 1,
          minHeight: "0",
          resize: "none",
          outline: "none",
          caretColor: showCursor ? "var(--accent-purple)" : "transparent",
          transition: "caret-color 0.1s"
        }}
        value={currentChapterText}
        onChange={(e) => setCurrentChapterText(e.target.value)}
        placeholder="ここに本文を入力してください..."
      />

      <div className="zen-mode__footer" style={{ 
        display: "flex", 
        justifyContent: "space-between", 
        alignItems: "center",
        padding: "16px 0",
        borderTop: "1px solid var(--border-color)",
        marginTop: "16px"
      }}>
        <div style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>
          💡 ヒント: Ctrl+Bでルビを挿入 | EscでZenモード終了
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <span style={{ fontSize: "0.85rem", color: "var(--accent-cyan)" }}>
            最終更新: {new Date().toLocaleTimeString()}
          </span>
        </div>
      </div>
    </div>
  );
};

const styles = {
  'text-sm': { fontSize: '15px' },
  'text-base': { fontSize: '17px' },
  'text-lg': { fontSize: '19px' },
  'text-xl': { fontSize: '21px' },
  'leading-tight': { lineHeight: '1.25' },
  'leading-normal': { lineHeight: '1.5' },
  'leading-relaxed': { lineHeight: '1.75' },
  'leading-loose': { lineHeight: '2.0' }
};