import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { InlineRevisionDiffModal } from '../../src/components/editor/InlineRevisionDiffModal';

describe('InlineRevisionDiffModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: jest.fn(),
    onApply: jest.fn(),
    onReject: jest.fn(),
    onHold: jest.fn(),
    onRegenerate: jest.fn(),
    originalText: '元のテキストです。',
    revisedText: '修正されたテキストです。',
    validationMessage: '',
    isValidating: false,
    isValid: true,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('基本レンダリング', () => {
    it('isOpenがfalseの場合、何もレンダリングしない', () => {
      render(<InlineRevisionDiffModal {...defaultProps} isOpen={false} />);
      expect(screen.queryByText('推敲結果の確認')).not.toBeInTheDocument();
    });

    it('isOpenがtrueの場合、モーダルが表示される', () => {
      render(<InlineRevisionDiffModal {...defaultProps} />);
      expect(screen.getByText('推敲結果の確認')).toBeInTheDocument();
    });

    it('原文と修正後テキストが表示される', () => {
      render(<InlineRevisionDiffModal {...defaultProps} />);
      expect(screen.getByText('元のテキストです。')).toBeInTheDocument();
      expect(screen.getByText('修正されたテキストです。')).toBeInTheDocument();
    });

    it('閉じるボタンが表示される', () => {
      render(<InlineRevisionDiffModal {...defaultProps} />);
      expect(screen.getByLabelText('閉じる')).toBeInTheDocument();
    });

    it('各アクションボタンが表示される', () => {
      render(<InlineRevisionDiffModal {...defaultProps} />);
      expect(screen.getByText('再生成')).toBeInTheDocument();
      expect(screen.getByText('保留')).toBeInTheDocument();
      expect(screen.getByText('却下')).toBeInTheDocument();
      expect(screen.getByText('適用')).toBeInTheDocument();
    });
  });

  describe('オーバーレイクリックで閉じる', () => {
    it('オーバーレイをクリックするとonCloseが呼ばれる', () => {
      render(<InlineRevisionDiffModal {...defaultProps} />);
      fireEvent.click(screen.getByTestId('modal-overlay') || screen.getByText('推敲結果の確認').closest('div')!);
      expect(defaultProps.onClose).toHaveBeenCalled();
    });
  });

  describe('各ボタンの動作', () => {
    it('閉じるボタンでonCloseが呼ばれる', () => {
      render(<InlineRevisionDiffModal {...defaultProps} />);
      fireEvent.click(screen.getByLabelText('閉じる'));
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it('適用ボタンでonApplyが呼ばれる', () => {
      render(<InlineRevisionDiffModal {...defaultProps} />);
      fireEvent.click(screen.getByText('適用'));
      expect(defaultProps.onApply).toHaveBeenCalled();
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it('却下ボタンでonRejectが呼ばれる', () => {
      render(<InlineRevisionDiffModal {...defaultProps} />);
      fireEvent.click(screen.getByText('却下'));
      expect(defaultProps.onReject).toHaveBeenCalled();
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it('保留ボタンでonHoldが呼ばれる', () => {
      render(<InlineRevisionDiffModal {...defaultProps} />);
      fireEvent.click(screen.getByText('保留'));
      expect(defaultProps.onHold).toHaveBeenCalled();
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it('再生成ボタンでonRegenerateが呼ばれる', () => {
      render(<InlineRevisionDiffModal {...defaultProps} />);
      fireEvent.click(screen.getByText('再生成'));
      expect(defaultProps.onRegenerate).toHaveBeenCalled();
    });
  });

  describe('バリデーション失敗時の警告表示', () => {
    it('isValidがfalseの場合、警告メッセージが表示される', () => {
      render(
        <InlineRevisionDiffModal
          {...defaultProps}
          isValid={false}
          validationMessage="原文が変更されています: text_changed"
        />
      );
      expect(screen.getByText('⚠ 原文が変更されています: text_changed')).toBeInTheDocument();
      expect(screen.getByText('原文が編集中に変更されています。適用すると意図しない変更が含まれる可能性があります。')).toBeInTheDocument();
    });

    it('isValidがtrueの場合、警告が表示されない', () => {
      render(
        <InlineRevisionDiffModal
          {...defaultProps}
          isValid={true}
          validationMessage="警告メッセージ"
        />
      );
      expect(screen.queryByText('⚠')).not.toBeInTheDocument();
    });
  });

  describe('検証中インジケーター', () => {
    it('isValidatingがtrueの場合、検証中インジケーターが表示される', () => {
      render(<InlineRevisionDiffModal {...defaultProps} isValidating={true} />);
      expect(screen.getByText('原文との整合性を検証中...')).toBeInTheDocument();
    });
  });

  describe('確認ダイアログ', () => {
    it('無効な状態で適用ボタンを押すと確認ダイアログが表示される', async () => {
      render(
        <InlineRevisionDiffModal
          {...defaultProps}
          isValid={false}
          validationMessage="原文が変更されています"
        />
      );

      fireEvent.click(screen.getByText('適用'));

      await waitFor(() => {
        expect(screen.getByText('原文が変更されています')).toBeInTheDocument();
      });

      expect(screen.getByText('キャンセル')).toBeInTheDocument();
      expect(screen.getByText('それでも適用')).toBeInTheDocument();
    });

    it('確認ダイアログでキャンセルすると適用されない', async () => {
      render(<InlineRevisionDiffModal {...defaultProps} isValid={false} />);

      fireEvent.click(screen.getByText('適用'));

      await waitFor(() => {
        expect(screen.getByText('キャンセル')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('キャンセル'));

      await waitFor(() => {
        expect(screen.queryByText('原文が変更されています')).not.toBeInTheDocument();
      });

      expect(defaultProps.onApply).not.toHaveBeenCalled();
    });

    it('確認ダイアログで「それでも適用」を押すと適用される', async () => {
      render(<InlineRevisionDiffModal {...defaultProps} isValid={false} />);

      fireEvent.click(screen.getByText('適用'));

      await waitFor(() => {
        expect(screen.getByText('それでも適用')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('それでも適用'));

      await waitFor(() => {
        expect(defaultProps.onApply).toHaveBeenCalled();
        expect(defaultProps.onClose).toHaveBeenCalled();
      });
    });
  });

  describe('モーダル外クリックで閉じる', () => {
    it('オーバーレイ部分をクリックすると閉じる', () => {
      const { container } = render(<InlineRevisionDiffModal {...defaultProps} />);
      const overlay = container.firstChild as HTMLElement;
      fireEvent.click(overlay);
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it('モーダル内部をクリックしても閉じない', () => {
      render(<InlineRevisionDiffModal {...defaultProps} />);
      const modal = screen.getByText('推敲結果の確認').closest('div')!;
      fireEvent.click(modal);
      expect(defaultProps.onClose).not.toHaveBeenCalled();
    });
  });

  describe('キーボード操作', () => {
    it('Escapeキーで閉じる', () => {
      render(<InlineRevisionDiffModal {...defaultProps} />);
      fireEvent.keyDown(document, { key: 'Escape' });
      expect(defaultProps.onClose).toHaveBeenCalled();
    });
  });

  describe('再生成ボタン', () => {
    it('再生成ボタンが無効化されている', () => {
      render(<InlineRevisionDiffModal {...defaultProps} />);
      const regenerateButton = screen.getByText('再生成');
      expect(regenerateButton).toBeDisabled();
    });
  });
});