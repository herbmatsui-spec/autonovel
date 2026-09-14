import { Node, mergeAttributes } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { RubyRenderer } from './RubyRenderer';

export interface RubyOptions {
  HTMLAttributes: Record<string, any>;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    ruby: {
      setRuby: (options: { ruby: string; rt: string; original?: string }) => ReturnType;
    };
  }
}

export const RubyExtension = Node.create<RubyOptions>({
  name: 'ruby',
  group: 'inline',
  inline: true,
  selectable: false,
  atom: true,

  addAttributes() {
    return {
      ruby: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute('data-ruby'),
        renderHTML: (attributes: Record<string, any>) => {
          return {
            'data-ruby': attributes.ruby,
          };
        },
      },
      rt: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute('data-rt'),
        renderHTML: (attributes: Record<string, any>) => {
          return {
            'data-rt': attributes.rt,
          };
        },
      },
      original: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute('data-original'),
        renderHTML: (attributes: Record<string, any>) => {
          return {
            'data-original': attributes.original,
          };
        },
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'ruby',
        getAttrs: (element: HTMLElement) => {
          return {
            ruby: element.getAttribute('data-ruby'),
            rt: element.getAttribute('data-rt'),
            original: element.getAttribute('data-original'),
          };
        },
      },
    ];
  },

  renderHTML({ node }: { node: any }) {
    const { ruby, rt, original } = node.attrs;
    
    if (!ruby || !rt) {
      return ['span', { 'data-invalid-ruby': true }, 0];
    }

    return [
      'ruby',
      { 'data-ruby': ruby, 'data-rt': rt, 'data-original': original },
      [
        'span',
        { class: 'ruby-base' },
        original || ruby,
      ],
      [
        'rt',
        { class: 'ruby-rt' },
        rt,
      ],
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(RubyRenderer);
  },

  addCommands() {
    return {
      setRuby:
        (options: { ruby: string; rt: string; original?: string }) =>
        ({ commands }: { commands: any }) => {
          return commands.insertContentAtCursor([
            {
              type: 'ruby',
              attrs: {
                ruby: options.ruby,
                rt: options.rt,
                original: options.original || options.ruby,
              },
            },
          ]);
        },
    };
  },
});

export { RubyRenderer };