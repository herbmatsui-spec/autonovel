import React, { useMemo } from 'react';
import { RichNovelEditor, RichNovelEditorRef } from '../editor/RichNovelEditor';

interface TipTapEditorProps {
  initialContent?: string;
  onChange?: (content: string) => void;
  readOnly?: boolean;
  className?: string;
}

export const TipTapEditor = React.forwardRef<RichNovelEditorRef, TipTapEditorProps>(({
  initialContent = '',
  onChange,
  readOnly = false,
  className = '',
}, ref) => {
  const [text, setText] = React.useState(initialContent);

  const metrics = useMemo(() => {
    const charCount = text.length;
    const dialogues = text.match(/「[^」]*」/g) || [];
    const dialogueChars = dialogues.reduce((acc, cur) => acc + cur.length - 2, 0);
    const dialogueRatio = charCount > 0 ? Math.round((dialogueChars / charCount) * 100) : 0;
    return {
      charCount,
      dialogueRatio,
    };
  }, [text]);

  const handleChange = (newText: string) => {
    setText(newText);
    onChange?.(newText);
  };

  return (
    <div className={`tiptap-studio-editor flex flex-col h-full bg-gray-900 text-gray-100 ${className}`}>
      {/* エディタステータスヘッダー */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-gray-950/70 text-xs text-gray-400">
        <div className="flex items-center gap-3">
          <span className="font-medium text-gray-300">TipTap 本文エディタ (v5.2)</span>
          <span className="text-gray-600">|</span>
          <span>文字数: <strong className="text-indigo-400 font-mono">{metrics.charCount}</strong> 字</span>
          <span className="text-gray-600">|</span>
          <span>会話文率: <strong className="text-emerald-400 font-mono">{metrics.dialogueRatio}%</strong></span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>オートセーブ有効</span>
        </div>
      </div>

      {/* TipTap 本文コア */}
      <div className="flex-1 overflow-y-auto p-4">
        <RichNovelEditor
          ref={ref}
          initialContent={initialContent}
          onChange={handleChange}
          readOnly={readOnly}
          className="min-h-[400px] font-serif leading-relaxed text-base"
        />
      </div>
    </div>
  );
});

TipTapEditor.displayName = 'TipTapEditor';

export default TipTapEditor;
