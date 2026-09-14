import React, { useState, useEffect, forwardRef, useImperativeHandle } from 'react';
import { EditorContent, useEditor, Editor as TiptapEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { RubyExtension } from '../../lib/tiptap/rubyExtension';

export interface RichNovelEditorRef {
  getContent: () => string;
  setContent: (content: string) => void;
  getEditor: () => TiptapEditor | null;
}

interface RichNovelEditorProps {
  initialContent?: string;
  onChange?: (content: string) => void;
  readOnly?: boolean;
  className?: string;
}

export const RichNovelEditor = forwardRef<RichNovelEditorRef, RichNovelEditorProps>(({
  initialContent = '',
  onChange,
  readOnly = false,
  className = ''
}, ref) => {
  const [content, setContent] = useState(initialContent);

  const editor = useEditor({
    extensions: [
      StarterKit,
      RubyExtension,
    ],
    content: initialContent,
    editable: !readOnly,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      const text = editor.getText();
      setContent(text);
      onChange?.(text);
    },
  }, [initialContent, readOnly, onChange]);

  useImperativeHandle(ref, () => ({
    getContent: () => editor?.getText() || '',
    setContent: (newContent: string) => {
      editor?.commands.setContent(newContent);
    },
    getEditor: () => editor,
  }), [editor]);

  if (!editor) {
    return null;
  }

  return (
    <div className={`rich-novel-editor ${className}`}>
      <EditorContent 
        editor={editor}
        className="tiptap-editor-content"
      />
    </div>
  );
});

RichNovelEditor.displayName = 'RichNovelEditor';