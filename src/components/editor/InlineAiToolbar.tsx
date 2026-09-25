import React, { useState } from 'react';
import { InlineRevisionDiffModal } from './InlineRevisionDiffModal';
import { useInlineRevision } from '../../hooks/useInlineRevision';

interface InlineAiToolbarProps {
  editorRef: React.RefObject<HTMLDivElement>;
  onRevisionRequest?: (text: string) => Promise<string>;
}

export const InlineAiToolbar: React.FC<InlineAiToolbarProps> = ({
  editorRef,
  onRevisionRequest,
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [originalText, setOriginalText] = useState('');
  const [revisedText, setRevisedText] = useState('');
  const [validationMessage, setValidationMessage] = useState('');
  const [isValidating, setIsValidating] = useState(false);

  const {
    status,
    proposal,
    diff,
    validationResult,
    generateProposal,
    apply,
    reject,
    hold,
    regenerate,
    reset,
  } = useInlineRevision({
    onApply: (revisedFullText) => {
      console.log('Applying revised text:', revisedFullText);
      setIsModalOpen(false);
      reset();
    },
    onReject: () => {
      setIsModalOpen(false);
      reset();
    },
    onHold: () => {
      setIsModalOpen(false);
      reset();
    },
    onError: (error) => {
      console.error('Revision error:', error);
    },
  });

  const handleRevisionClick = async () => {
    if (!editorRef.current) return;

    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;

    const range = selection.getRangeAt(0);
    if (!editorRef.current.contains(range.commonAncestorContainer)) return;

    const selectedText = selection.toString();
    if (!selectedText.trim()) return;

    const editorElement = editorRef.current;
    const fullText = editorElement.innerText || editorElement.textContent || '';
    const start = fullText.indexOf(selectedText);
    const end = start + selectedText.length;

    if (start === -1) return;

    setIsValidating(true);
    setOriginalText(selectedText);

    try {
      await generateProposal(
        fullText,
        { start, end },
        editorRef.current,
        '推敲してください',
        'gpt-4'
      );
    } catch (error) {
      console.error('Revision generation failed:', error);
    } finally {
      setIsValidating(false);
    }
  };

  const handleProposalReady = (proposal: any) => {
    if (proposal) {
      setRevisedText(proposal.revisedText);
      setIsModalOpen(true);
    }
  };

  React.useEffect(() => {
    if (diff) {
      console.log('Diff computed:', diff);
    }
  }, [diff]);

  React.useEffect(() => {
    if (validationResult) {
      if (!validationResult.isValid) {
        setValidationMessage(`原文が変更されています: ${validationResult.mismatchReason}`);
      } else {
        setValidationMessage('');
      }
    }
  }, [validationResult]);

  if (!editorRef.current) return null;

  return (
    <>
      <div className="inline-ai-toolbar">
        <button
          className="toolbar-button revision-button"
          onClick={handleRevisionClick}
          disabled={status === 'generating' || status === 'applying' || isValidating}
          title="選択範囲を推敲"
        >
          {status === 'generating' ? '生成中...' : '✨ 推敲'}
        </button>
      </div>

      <InlineRevisionDiffModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onApply={() => {
          // apply is handled by the hook
          setIsModalOpen(false);
        }}
        onReject={reject}
        onHold={hold}
        onRegenerate={regenerate}
        originalText={originalText}
        revisedText={revisedText}
        validationMessage={validationMessage}
        isValidating={isValidating}
      />
    </>
  );
};