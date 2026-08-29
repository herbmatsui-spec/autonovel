import { Extension } from '@tiptap/core'
import type { Editor, Range } from '@tiptap/core'
import { ReactRenderer } from '@tiptap/react'
import Suggestion, { type SuggestionOptions } from '@tiptap/suggestion'
import type { RefObject } from 'react'
import type { ReactNode } from 'react'
import { Command, CommandItem, CommandList } from 'cmdk'

const SlashCommand = Extension.create({
  name: 'slashCommand',
  
  addOptions() {
    return {
      suggestion: {
        char: '/',
        command: ({ editor, range, props }: { editor: Editor; range: Range; props: { command: (props: { editor: Editor; range: Range }) => void } }) => {
          props.command({ editor, range })
        },
      } as SuggestionOptions,
    }
  },
  
  addProseMirrorPlugins() {
    return [
      Suggestion({
        editor: this.editor,
        ...this.options.suggestion,
      }),
    ]
  },
})

// Define the shape of our suggestion items
interface SlashCommandItem {
  title: string
  description: string
  icon?: ReactNode
  command: (props: { editor: Editor; range: Range }) => void
}

// Render the suggestion menu using cmdk
const renderItems = (elementRef?: RefObject<Element> | null) => {
  let component: ReactRenderer | null = null
  let popup: Instance<Props>[] | null = null

  return {
    onStart: (props: { editor: Editor; clientRect: DOMRect }) => {
      // Create the cmdk command palette component
      component = new ReactRenderer(SlashCommandMenu, {
        props,
        editor: props.editor,
      })

      // Position the menu using tippy.js
      // @ts-ignore
      popup = tippy('body', {
        getReferenceClientRect: props.clientRect,
        appendTo: () => (elementRef ? elementRef.current : document.body),
        content: component.element,
        showOnCreate: true,
        interactive: true,
        trigger: 'manual',
        placement: 'bottom-start',
      })
    },
    
    onUpdate: (props: { editor: Editor; clientRect: GetReferenceClientRect }) => {
      component?.updateProps(props)
      
      popup?.[0]?.setProps({
        getReferenceClientRect: props.clientRect,
      })
    },
    
    onKeyDown: (props: { event: KeyboardEvent }) => {
      // Handle escape key to close the menu
      if (props.event.key === 'Escape') {
        popup?.[0]?.hide()
        return true
      }
      
      // Let cmdk handle other keyboard navigation
      // @ts-ignore
      return component?.ref?.onKeyDown(props)
    },
    
    onExit: () => {
      popup?.[0]?.destroy()
      component?.destroy()
    },
  }
}

// Slash command menu component using cmdk
function SlashCommandMenu({ editor }: { editor: Editor }) {
  // Define available slash commands
  const items: SlashCommandItem[] = [
    {
      title: '見出し 1',
      description: '大見出しを挿入',
      command: ({ editor }) => {
        editor.chain().focus().toggleHeading({ level: 1 }).run()
      }
    },
    {
      title: '見出し 2',
      description: '中見出しを挿入',
      command: ({ editor }) => {
        editor.chain().focus().toggleHeading({ level: 2 }).run()
      }
    },
    {
      title: '見出し 3',
      description: '小見出しを挿入',
      command: ({ editor }) => {
        editor.chain().focus().toggleHeading({ level: 3 }).run()
      }
    },
    {
      title: '箇条書きリスト',
      description: '箇条書きリストを挿入',
      command: ({ editor }) => {
        editor.chain().focus().toggleBulletList().run()
      }
    },
    {
      title: '番号付きリスト',
      description: '番号付きリストを挿入',
      command: ({ editor }) => {
        editor.chain().focus().toggleOrderedList().run()
      }
    },
    {
      title: '引用ブロック',
      description: '引用ブロックを挿入',
      command: ({ editor }) => {
        editor.chain().focus().toggleBlockquote().run()
      }
    },
    {
      title: 'コードブロック',
      description: 'コードブロックを挿入',
      command: ({ editor }) => {
        editor.chain().focus().toggleCodeBlock().run()
      }
    },
    {
      title: '水平線',
      description: '水平線を挿入',
      command: ({ editor }) => {
        editor.chain().focus().setHorizontalRule().run()
      }
    }
  ]

  return (
    <Command
      id="slash-command-menu"
      className="relative w-[260px] max-h-[400px]"
    >
      <Command.Input
        placeholder="コマンドを入力..."
        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-accent-indigo focus:border-transparent"
      />
      <CommandList>
        {items.map((item, index) => (
          <SlashCommandItem
            key={index}
            item={item}
            editor={editor}
          />
        ))}
      </CommandList>
    </Command>
  )
}

// Individual slash command item
function SlashCommandItem({ 
  item, 
  editor 
}: { 
  item: SlashCommandItem 
  editor: Editor 
}) {
  return (
    <CommandItem
      onSelect={() => {
        item.command({ editor: editor, range: editor.state.selection as Range })
      }}
      className="flex px-3 py-2 text-sm"
    >
      <div className="flex-shrink-0 flex items-center justify-center w-6 h-6">
        {/* Icon placeholder - could be replaced with actual icons */}
        <span className="text-accent-indigo">{item.title.charAt(0)}</span>
      </div>
      <div className="flex-1 pl-2">
        <div className="font-medium">{item.title}</div>
        <div className="text-xs text-gray-500">{item.description}</div>
      </div>
    </CommandItem>
  )
}

// Export the extension and render function
export { SlashCommand, renderItems }