import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { SlashCommand } from './extensions/SlashCommandExtension'
import { EditorBubble } from './BubbleMenu'
import ImageUpload, { uploadImage } from './extensions/ImageUploadExtension'
import { AIAutocomplete } from './extensions/AIAutocompleteExtension'

interface TiptapEditorProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  onImageUpload?: (file: File) => Promise<string> | string
  apiKey?: string
}

export function TiptapEditor({
  value,
  onChange,
  placeholder = 'Start writing...',
  disabled = false,
  onImageUpload,
  apiKey,
}: TiptapEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({
        placeholder,
      }),
      SlashCommand,
      ImageUpload.extend({
        addProseMirrorPlugins() {
          return [
            // Handle pasted images
            ...this.parent?.()?.filter(p => p.name === 'dropcursor') || [],
            ...this.parent?.()?.filter(p => p.name === 'gapcursor') || [],
          ]
        },
      }),
      AIAutocomplete,
    ],
    content: value || '<p><br></p>',
    editable: !disabled,
    immediatelyRender: false,
  })

  // Update editor content when value prop changes
  const isUpdatingRef = React.useRef(false)

  React.useEffect(() => {
    if (!isUpdatingRef.current && editor) {
      isUpdatingRef.current = true
      editor.commands.setContent(value || '<p><br></p>')
      isUpdatingRef.current = false
    }
  }, [value, editor])

  // Update parent state when editor content changes
  React.useEffect(() => {
    if (!editor) return
    
    const handler = () => {
      if (!isUpdatingRef.current) {
        isUpdatingRef.current = true
        const html = editor.getHTML()
        // Convert HTML to plain text for compatibility with existing code
        const plainText = htmlToPlainText(html)
        onChange(plainText)
        isUpdatingRef.current = false
      }
    }
    
    editor.on('update', handler)
    return () => {
      editor.off('update', handler)
    }
  }, [editor, onChange])

  if (!editor) {
    return <div>Loading editor...</div>
  }

  const editorClassName = disabled
    ? 'min-h-[200px] border border-gray-300 rounded-lg opacity-50 pointer-events-none'
    : 'min-h-[200px] border border-gray-300 rounded-lg'

  return (
    <div className="relative">
      <EditorBubble className="pointer-events-none">
        {/* Bubble menu buttons */}
        <div className="flex gap-1 px-2 py-1 bg-white rounded-lg shadow-md border border-gray-200">
          <button
            onClick={() => editor.chain().focus().toggleBold().run()}
            disabled={!editor.isEditable}
            className="hover:bg-gray-100 rounded px-2 py-1 text-sm font-medium"
            title="太字 (Ctrl+B)"
          >
            B
          </button>
          <button
            onClick={() => editor.chain().focus().toggleItalic().run()}
            disabled={!editor.isEditable}
            className="hover:bg-gray-100 rounded px-2 py-1 text-sm font-medium"
            title="斜体 (Ctrl+I)"
          >
            I
          </button>
          <button
            onClick={() => editor.chain().focus().toggleUnderline().run()}
            disabled={!editor.isEditable}
            className="hover:bg-gray-100 rounded px-2 py-1 text-sm font-medium"
            title="下線 (Ctrl+U)"
          >
            U
          </button>
          <button
            onClick={() => editor.chain().focus().toggleCode().run()}
            disabled={!editor.isEditable}
            className="hover:bg-gray-100 rounded px-2 py-1 text-sm font-medium"
            title="コード"
          >
            </button>
          {/* Image upload button */}
          <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={async (e: React.ChangeEvent<HTMLInputElement>) => {
              const file = e.target.files?.[0]
              if (!file) return
              
              try {
                // Use the provided upload function or fall back to default
                const url = onImageUpload 
                  ? await onImageUpload(file)
                  : await uploadImage(file)
                
                // Insert the image at the current selection
                editor.chain().focus().setImage({ src: url, alt: file.name }).run()
                
                // Reset the input
                e.target.value = ''
              } catch (error) {
                console.error('Failed to upload image:', error)
                alert('画像のアップロードに失敗しました')
              }
            }}
          >
            </input>
          <label
            htmlFor="image-upload"
            onClick={(e: React.MouseEvent<HTMLLabelElement, MouseEvent>) => {
              // Find the associated input and trigger click
              const input = e.currentTarget.parentElement?.querySelector('input[type="file"]')
              if (input) {
                input.click()
              }
            }}
            className="flex items-center justify-center w-6 h-6 rounded hover:bg-gray-100"
            title="画像をアップロード"
          >
            📎
          </label>
        </div>
      </EditorBubble>
      <EditorContent 
        editor={editor} 
        className={editorClassName}
      />
    </div>
  )
}

// Simple HTML to plain text converter
function htmlToPlainText(html: string): string {
  const temp = document.createElement('div')
  temp.innerHTML = html
  return temp.textContent || temp.innerText || ''
}

// Import React at the top
import React from 'react'