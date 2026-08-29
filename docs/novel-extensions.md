# Novel.sh Extensions Implementation Patterns

## Overview

Novel.sh implements several custom Tiptap extensions to provide its Notion-like WYSIWYG experience. This document summarizes the key implementation patterns that can be adapted for autonovel.

## Extension Files Structure

```
packages/headless/src/extensions/
├── ai-highlight.ts       # AI-generated text highlighting
├── custom-keymap.ts      # Custom keyboard shortcuts
├── image-resizer.tsx     # Image resize functionality
├── mathematics.ts        # LaTeX math support
├── slash-command.tsx    # Slash command (/) menu
├── twitter.tsx          # Twitter/X embed
├── updated-image.ts     # Extended image node
└── index.ts            # Exports all extensions
```

## 1. Slash Command Extension (slash-command.tsx)

### Pattern Overview

The slash command is built using `@tiptap/suggestion` package with ReactRenderer for the popup UI.

### Key Components

1. **Extension Definition** (`Command`):
   - Uses `Extension.create()` with `addOptions()` to define suggestion configuration
   - `char: "/"` sets the trigger character
   - `addProseMirrorPlugins()` adds the Suggestion plugin

2. **Rendering** (`renderItems`):
   - Uses `ReactRenderer` to mount a React component
   - Uses `tippy.js` for positioning the popup
   - Manages lifecycle (onStart, onUpdate, onKeyDown, onExit)

3. **Suggestion Items** (`SuggestionItem` interface):
   - `title`: Display text
   - `description`: Helper text
   - `icon`: ReactNode for icon
   - `searchTerms`: For filtering
   - `command`: Function to execute

### Code Structure

```tsx
// Extension creation
const Command = Extension.create({
  name: "slash-command",
  addOptions() {
    return {
      suggestion: {
        char: "/",
        command: ({ editor, range, props }) => {
          props.command({ editor, range });
        },
      } as SuggestionOptions,
    };
  },
  addProseMirrorPlugins() {
    return [
      Suggestion({
        editor: this.editor,
        ...this.options.suggestion,
      }),
    ];
  },
});

// Rendering with tippy.js
const renderItems = (elementRef?) => {
  return {
    onStart: (props) => {
      component = new ReactRenderer(EditorCommandOut, { props, editor });
      popup = tippy("body", {
        getReferenceClientRect: props.clientRect,
        content: component.element,
        placement: "bottom-start",
      });
    },
    // ... onUpdate, onKeyDown, onExit
  };
};
```

## 2. AI Highlight Extension (ai-highlight.ts)

### Pattern Overview

A custom Mark extension that highlights AI-generated text with a specific style. Uses `==text==` syntax.

### Key Components

1. **Mark Creation**: Uses `Mark.create()` instead of `Extension.create()`
2. **Input/Paste Rules**: Regex patterns for automaticMark creation
3. **Commands**: `setAIHighlight`, `toggleAIHighlight`, `unsetAIHighlight`

### Code Structure

```tsx
export const inputRegex = /(?:^|\s)((?:==)((?:[^~=]+))(?:==))$/;
export const pasteRegex = /(?:^|\s)((?:==)((?:[^~=]+))(?:==))/g;

export const AIHighlight = Mark.create({
  name: "ai-highlight",

  addAttributes() {
    return {
      color: {
        default: null,
        parseHTML: (element) => element.getAttribute("data-color"),
        renderHTML: (attributes) => ({
          "data-color": attributes.color,
          style: `background-color: ${attributes.color}`,
        }),
      },
    };
  },

  addCommands() {
    return {
      setAIHighlight: (attributes) => ({ commands }) => {
        return commands.setMark(this.name, attributes);
      },
      toggleAIHighlight: (attributes) => ({ commands }) => {
        return commands.toggleMark(this.name, attributes);
      },
      // ...
    };
  },

  addInputRules() {
    return [
      markInputRule({ find: inputRegex, type: this.type }),
    ];
  },
});
```

## 3. Image Resizer (image-resizer.tsx)

### Pattern Overview

Uses `react-moveable` library to provide drag handles for image resizing.

### Key Components

1. **Moveable Component**: From react-moveable library
2. **Selection Detection**: Uses `editor.isActive("image")`
3. **Size Update**: Updates image attributes via `setImage` command

### Code Structure

```tsx
export const ImageResizer: FC = () => {
  const { editor } = useCurrentEditor();

  if (!editor?.isActive("image")) return null;

  const updateMediaSize = () => {
    const imageInfo = document.querySelector(".ProseMirror-selectednode");
    if (imageInfo) {
      const setImage = editor.commands.setImage as (options) => boolean;
      setImage({
        src: imageInfo.src,
        width: Number(imageInfo.style.width.replace("px", "")),
        height: Number(imageInfo.style.height.replace("px", "")),
      });
    }
  };

  return (
    <Moveable
      target={document.querySelector(".ProseMirror-selectednode")}
      resizable={true}
      scalable={true}
      onResizeEnd={updateMediaSize}
    />
  );
};
```

## 4. Updated Image (updated-image.ts)

### Pattern Overview

Extends the base Tiptap Image extension to add width/height attributes.

### Code Structure

```tsx
const UpdatedImage = Image.extend({
  name: "image",
  addAttributes() {
    return {
      ...this.parent?.(),
      width: { default: null },
      height: { default: null },
    };
  },
});
```

## 5. Custom Keymap (custom-keymap.ts)

### Pattern Overview

Adds custom keyboard shortcut behavior. In this case, `Mod-a` (Cmd/Ctrl+A) is customized to select entire node boundaries.

### Code Structure

```tsx
const CustomKeymap = Extension.create({
  name: "CustomKeymap",

  addKeyboardShortcuts() {
    return {
      "Mod-a": ({ editor }) => {
        const { state } = editor;
        const startNodePos = state.tr.selection.$from.start();
        const endNodePos = state.tr.selection.$to.end();
        // If selection doesn't span full node, extend it
        // ...
        return true; // handled
      },
    };
  },
});
```

## 6. Bubble Menu Components

### EditorBubble (editor-bubble.tsx)

Wraps Tiptap's BubbleMenu with custom shouldShow logic:

```tsx
const shouldShow: BubbleMenuProps["shouldShow"] = ({ editor, state }) => {
  const { selection } = state;
  const { empty } = selection;

  // Don't show if:
  // - editor not editable
  // - image selected
  // - selection empty
  // - node selection (for drag handles)
  if (!editor.isEditable || editor.isActive("image") || empty || isNodeSelection(selection)) {
    return false;
  }
  return true;
};
```

## 7. Command Menu (cmdk-based)

### Pattern Overview

Uses `cmdk` (command menu library) for keyboard navigation in slash command popup.

### Key Components

1. **EditorCommand**: Wraps `Command` from cmdk
2. **EditorCommandItem**: Individual command items
3. **EditorCommandList**: List container

### Code Structure

```tsx
export const EditorCommand = forwardRef<HTMLDivElement, ComponentPropsWithoutRef<typeof Command>>(
  ({ children, className, ...rest }, ref) => {
    const [query, setQuery] = useAtom(queryAtom);

    return (
      <Command ref={ref} id="slash-command" onKeyDown={(e) => e.stopPropagation()}>
        <Command.Input value={query} onValueChange={setQuery} style={{ display: "none" }} />
        {children}
      </Command>
    );
  },
);
```

## Integration Pattern (apps/web)

### Editor.tsx

Uses `EditorProvider` and Jotai for state management:

```tsx
export const EditorRoot: FC<EditorRootProps> = ({ children }) => {
  const tunnelInstance = useRef(tunnel()).current;

  return (
    <Provider store={novelStore}>
      <EditorCommandTunnelContext.Provider value={tunnelInstance}>
        {children}
      </EditorCommandTunnelContext.Provider>
    </Provider>
  );
};

export const EditorContent = forwardRef<HTMLDivElement, EditorContentProps>(
  ({ className, children, initialContent, ...rest }, ref) => (
    <div ref={ref} className={className}>
      <EditorProvider {...rest} content={initialContent}>
        {children}
      </EditorProvider>
    </div>
  ),
);
```

## autonovel Adaptation Notes

### Key Differences

1. **State Management**: Novel.sh uses Jotai; autonovel uses Zustand
   - Replace Jotai atoms with Zustand store selectors

2. **Tunnel Pattern**: Novel.sh uses `tunnel-rat` for component tunneling
   - May not be necessary for autonovel's simpler use case

3. **AI Integration**: Novel.sh uses Vercel AI SDK
   - autonovel should use existing apiClient wrapper

### Recommended Simplifications

1. **Slash Commands**: Can simplify by removing cmdk dependency and using basic React state
2. **AI Highlight**: Can be simplified or omitted initially
3. **Image Resizer**: Can use simpler resize handles initially
4. **Twitter/Math**: Can be deferred to later phases

### Minimal Implementation Order

1. Start with basic Tiptap editor (StarterKit + Placeholder)
2. Add slash command with simple dropdown
3. Add bubble menu for formatting
4. Add basic image support
5. Add AI autocomplete (++ trigger) in later phase