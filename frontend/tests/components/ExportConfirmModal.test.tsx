import { render, screen, fireEvent } from '@testing-library/react';
import { ExportConfirmModal } from '@/components/common/ExportConfirmModal';
import { ExportHandoffSummary, ExportTarget } from '@/types/export';

describe('ExportConfirmModal', () => {
  const defaultSummary: ExportHandoffSummary = {
    targets: [
      {
        bookId: '1',
        chapterId: '1',
        branchId: 'main',
        version: 'saved',
        destination: 'zip',
        label: '第1話 (mainブランチ・保存版)',
        wordCount: 1000,
        lastSavedAt: new Date().toISOString(),
      },
    ],
    primaryTarget: {
      bookId: '1',
      chapterId: '1',
      branchId: 'main',
      version: 'saved',
      destination: 'zip',
      label: '第1話 (mainブランチ・保存版)',
      wordCount: 1000,
      lastSavedAt: new Date().toISOString(),
    },
    warnings: [],
  };

  test('summary 渡しで正しく表示される', () => {
    const onClose = vi.fn();
    const onConfirm = vi.fn();

    render(
      <ExportConfirmModal
        isOpen={true}
        onClose={onClose}
        summary={defaultSummary}
        onConfirm={onConfirm}
      />
    );

    // タイトルが表示されることを確認
    expect(screen.getByText(/出力前確認/)).toBeInTheDocument();
    
    // 各フィールドのラベルと値が正しく表示されることを確認
    // ブランチフィールド
    const branchLabels = screen.getAllByText(/ブランチ/);
    // index 1がラベル元素（index 0はタイトルの一部、index 2はプライマリターゲットテキスト）
    const branchLabel = branchLabels[1];
    expect(branchLabel).toBeInTheDocument();
    // ブランチラベルの親要素の次の兄弟要素（値のコンテナ）から値を取得
    const branchValueContainer = branchLabel.parentElement?.nextElementSibling;
    expect(branchValueContainer?.querySelector('div')).toHaveTextContent('main');
    
    // 版フィールド
    const versionLabels = screen.getAllByText(/版/);
    // index 1がラベル元素（index 0はタイトルの一部、index 2はプライマリターゲットテキスト）
    const versionLabel = versionLabels[1];
    expect(versionLabel).toBeInTheDocument();
    // 版ラベルの親要素の次の兄弟要素（値のコンテナ）から値を取得
    const versionValueContainer = versionLabel.parentElement?.nextElementSibling;
    expect(versionValueContainer?.querySelector('div')).toHaveTextContent('保存版');
    
    // 行き先フィールド
    const destinationLabels = screen.getAllByText(/行き先/);
    // index 1がラベル元素
    const destinationLabel = destinationLabels[1];
    expect(destinationLabel).toBeInTheDocument();
    // 行き先ラベルの親要素の次の兄弟要素（値のコンテナ）から値を取得
    const destinationValueContainer = destinationLabel.parentElement?.nextElementSibling;
    expect(destinationValueContainer?.querySelector('div')).toHaveTextContent('ZIPダウンロード');
    
    // 文字数フィールド
    const wordCountLabels = screen.getAllByText(/文字数/);
    // index 1がラベル元素
    const wordCountLabel = wordCountLabels[1];
    expect(wordCountLabel).toBeInTheDocument();
    // 文字数ラベルの親要素の次の兄弟要素（値のコンテナ）から値を取得
    const wordCountValueContainer = wordCountLabel.parentElement?.nextElementSibling;
    expect(wordCountValueContainer?.querySelector('div')).toHaveTextContent('1000字');
    
    // プライマリターゲットセクションが表示されることを確認
    expect(screen.getByText(/📤 出力実行対象/)).toBeInTheDocument();
    
    // キャンセルボタンと出力実行ボタンが存在することを確認
    expect(screen.getByRole('button', { name: /キャンセル/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /出力実行/ })).toBeInTheDocument();
  });

  test('警告配列があるとき黄色バナー表示', () => {
    const summaryWithWarnings: ExportHandoffSummary = {
      ...defaultSummary,
      warnings: ['保存版と現在編集版で 1,200 字の差分があります'],
    };

    const onClose = vi.fn();
    const onConfirm = vi.fn();

    render(
      <ExportConfirmModal
        isOpen={true}
        onClose={onClose}
        summary={summaryWithWarnings}
        onConfirm={onConfirm}
      />
    );

    // 警告バナーが表示されることを確認
    expect(screen.getByText(/注意/)).toBeInTheDocument();
    expect(screen.getByText(/保存版と現在編集版で 1,200 字の差分があります/)).toBeInTheDocument();
    // 警告バナーのスタイルを確認（背景色が黄色系であることを確認）
    const warningElement = screen.getByText(/注意/);
    expect(warningElement).toBeInTheDocument();
    // より具体的には、黄色のバナー要素自体を取得して確認
    const bannerElement = warningElement.closest('div')?.closest('div');
    expect(bannerElement).toHaveClass('bg-yellow-50');
  });

  test('「出力実行」クリックで onConfirm に正しい ExportTarget 渡る', () => {
    const onClose = vi.fn();
    const onConfirm = vi.fn();

    render(
      <ExportConfirmModal
        isOpen={true}
        onClose={onClose}
        summary={defaultSummary}
        onConfirm={onConfirm}
      />
    );

    // 出力実行ボタンをクリック
    const confirmButton = screen.getByRole('button', { name: /出力実行/ });
    fireEvent.click(confirmButton);

    // onConfirm が正しい引数で呼ばれたことを確認
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledWith(
      expect.objectContaining({
        bookId: '1',
        chapterId: '1',
        branchId: 'main',
        version: 'saved',
        destination: 'zip',
      })
    );
  });

  test('Escape キーで onClose 呼ばれる', () => {
    const onClose = vi.fn();
    const onConfirm = vi.fn();

    render(
      <ExportConfirmModal
        isOpen={true}
        onClose={onClose}
        summary={defaultSummary}
        onConfirm={onConfirm}
      />
    );

    // Escape キーを押下
    fireEvent.keyDown(document.body, { key: 'Escape' });

    // onClose が呼ばれたことを確認
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test('フォーカストラップ動作 (基本的なボタンアクセシビリティ)', () => {
    const onClose = vi.fn();
    const onConfirm = vi.fn();

    render(
      <ExportConfirmModal
        isOpen={true}
        onClose={onClose}
        summary={defaultSummary}
        onConfirm={onConfirm}
      />
    );

    // ボタンが存在し、クリックできることを確認
    const cancelButton = screen.getByRole('button', { name: /キャンセル/ });
    const confirmButton = screen.getByRole('button', { name: /出力実行/ });
    
    expect(cancelButton).toBeInTheDocument();
    expect(confirmButton).toBeInTheDocument();
    
    // ボタンがクリックできることを確認
    fireEvent.click(cancelButton);
    expect(onClose).toHaveBeenCalledTimes(1);
    
    fireEvent.click(confirmButton);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });
});