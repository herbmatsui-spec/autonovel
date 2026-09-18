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
    
    // 各フィールドのラベルが存在することを確認（class名とテキストの組み合わせで一意に特定）
    // font-mediumクラスを持つすべての要素を取得し、テキストでフィルタリング
    const fontMediumElements = Array.from(document.getElementsByClassName('font-medium'));
    
    const branchLabel = fontMediumElements.find(el => el.textContent.includes('ブランチ'));
    expect(branchLabel).toBeInTheDocument();
    
    const versionLabel = fontMediumElements.find(el => el.textContent.includes('版'));
    expect(versionLabel).toBeInTheDocument();
    
    const destinationLabel = fontMediumElements.find(el => el.textContent.includes('行き先'));
    expect(destinationLabel).toBeInTheDocument();
    
    const wordCountLabel = fontMediumElements.find(el => el.textContent.includes('文字数'));
    expect(wordCountLabel).toBeInTheDocument();
    
    // 各フィールドの値が正しく表示されることを確認
    // ブランチの値 "main" - ラベルの次の兄弟要素として存在することを確認
    expect(branchLabel.nextElementSibling).toHaveTextContent('main');
    
    // 版の値 "保存版" - ラベルの次の兄弟要素として存在することを確認
    expect(versionLabel.nextElementSibling).toHaveTextContent('保存版');
    
    // 行き先の値 "ZIPダウンロード" - ラベルの次の兄弟要素として存在することを確認
    expect(destinationLabel.nextElementSibling).toHaveTextContent('ZIPダウンロード');
    
    // 文字数の値 "1,000字" - ラベルの次の兄弟要素として存在することを確認
    expect(wordCountLabel.nextElementSibling).toHaveTextContent('1,000字');
    
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