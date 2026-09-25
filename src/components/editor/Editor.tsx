import React, { useRef, useCallback } from 'react';
import { InlineAiToolbar } from './InlineAiToolbar';

interface EditorProps {
  initialContent?: string;
  onContentChange?: (content: string) => void;
  readOnly?: boolean;
  className?: string;
}

export const Editor: React.FC<EditorProps> = ({
  initialContent = '',
  onContentChange,
  readOnly = false,
  className = '',
}) => {
  const editorRef = useRef<HTMLDivElement>(null);

  const handleInput = useCallback(() => {
    if (editorRef.current && onContentChange) {
      onContentChange(editorRef.current.innerText || '');
    }
  }, [onContentChange]);

  const handleSelectionChange = useCallback(() => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;

    const range = selection.getRangeAt(0);
    if (!editorRef.current?.contains(range.commonAncestorContainer)) {
      return;
    }

    const selectedText = selection.toString();
    const hasSelection = selectedText.trim().length > 0;

    return { hasSelection, range, text: selectedText };
  }, []);

  const getEditorContent = useCallback(() => {
    return editorRef.current?.innerText || '';
  }, []);

  const setEditorContent = useCallback((content: string) => {
    if (editorRef.current) {
      editorRef.current.innerText = content;
      onContentChange?.(content);
    }
  }, [onContentChange]);

  const insertText = useCallback((text: string) => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;

    const range = selection.getRangeAt(0);
    if (!editorRef.current?.contains(range.commonAncestorContainer)) return;

    range.deleteContents();
    range.insertNode(document.createTextNode(text));
    range.collapse(false);
    selection.removeAllRanges();
    selection.addRange(range);

    handleInput();
  }, [handleInput]);

  const replaceSelection = useCallback((text: string) => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;

    const range = selection.getRangeAt(0);
    if (!editorRef.current?.contains(range.commonAncestorContainer)) return;

    range.deleteContents();
    range.insertNode(document.createTextNode(text));
    range.collapse(false);
    selection.removeAllRanges();
    selection.addRange(range);

    handleInput();
  }, [handleInput]);

  return (
    <div
      className={`editor ${className}`}
      ref={editorRef}
      contentEditable={!readOnly}
      onInput={handleInput}
      onKeyDown={(e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          document.execCommand('insertLineBreak');
          handleInput();
        }
      }}
      suppressContentEditableWarning
      spellCheck={false}
    >
      {initialContent}
    </div>
  );
};

export const useEditor = () => {
  const editorRef = useRef<HTMLDivElement>(null);

  const getSelection = useCallback(() => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return null;

    const range = selection.getRangeAt(0);
    if (!editorRef.current?.contains(range.commonAncestorContainer)) {
      return null;
    }

    return {
      text: selection.toString(),
      range,
      start: 0,
      end: 0,
    };
  }, []);

  const replaceSelection = useCallback((text: string) => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;

    const range = selection.getRangeAt(0);
    if (!editorRef.current?.contains(range.commonAncestorContainer)) return;

    range.deleteContents();
    range.insertNode(document.createTextNode(text));
    range.collapse(false);
    selection.removeAllRanges();
    selection.addRange(range);
  }, []);

  return { editorRef, getSelection, replaceSelection };
};