import React from 'react';
import { NodeViewWrapper, type NodeViewProps } from '@tiptap/react';

export const RubyRenderer: React.FC<NodeViewProps> = ({ node }) => {
  const { ruby, rt, original } = (node.attrs || {}) as {
    ruby?: string;
    rt?: string;
    original?: string;
  };
  return (
    <NodeViewWrapper as="span" className="inline-ruby">
      <ruby>
        {original || ruby}
        <rt className="ruby-rt text-xs text-purple-400">{rt}</rt>
      </ruby>
    </NodeViewWrapper>
  );
};
