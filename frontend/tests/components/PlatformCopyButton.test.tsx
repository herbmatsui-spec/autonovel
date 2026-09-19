// Step 23: 字下げトグルとコピー動作のVitest単体テスト。
// 注意: この環境（Node.js 24 + vitest 1.6）では vitest からの名前付き import が
// undefined になるため、globals: true 設定のグローバルAPI（describe/it/expect/vi）を使用する。

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PlatformCopyButton } from '../../src/components/common/PlatformCopyButton';
import { apiFetch, handleResponse } from '../../src/api/client';
import { useToast } from '../../src/hooks/useToast';

vi.mock('../../src/hooks/useToast');
vi.mock('../../src/api/client');

const mockAddToast = vi.fn();
(useToast as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
  addToast: mockAddToast,
  removeToast: vi.fn(),
  toasts: [],
});

const mockApiFetch = vi.fn();
const mockHandleResponse = vi.fn();
(apiFetch as unknown as ReturnType<typeof vi.fn>).mockImplementation(mockApiFetch);
(handleResponse as unknown as ReturnType<typeof vi.fn>).mockImplementation(mockHandleResponse);

describe('PlatformCopyButton', () => {
  const mockTitle = '第1章 旅立ち';
  const mockBody = '「行くぞ」\n旅人は言った。';

  beforeEach(() => {
    vi.clearAllMocks();
    mockAddToast.mockClear();
    mockApiFetch.mockClear();
    mockHandleResponse.mockClear();

    // Mock navigator.clipboard.writeText
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
      configurable: true,
    });
  });

  it('renders three platform buttons', () => {
    render(<PlatformCopyButton title={mockTitle} body={mockBody} />);

    expect(screen.getByText('なろう')).toBeInTheDocument();
    expect(screen.getByText('カクヨム')).toBeInTheDocument();
    expect(screen.getByText('アルファ')).toBeInTheDocument();
  });

  it('calls apiFetch with correct payload for narou', async () => {
    const mockResponse = {
      ok: true,
      json: vi.fn().mockResolvedValue({
        title: mockTitle,
        foreword: '',
        body: '　「行くぞ」\n　旅人は言った。',
        afterword: '',
        total_characters: 20,
        platform: 'narou',
      }),
    };

    mockApiFetch.mockResolvedValue(mockResponse);
    mockHandleResponse.mockResolvedValue({
      title: mockTitle,
      foreword: '',
      body: '　「行くぞ」\n　旅人は言った。',
      afterword: '',
      total_characters: 20,
      platform: 'narou',
    });

    render(<PlatformCopyButton title={mockTitle} body={mockBody} />);

    fireEvent.click(screen.getByText('なろう'));

    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalledWith(
        '/api/export/copy/',
        expect.objectContaining({
          method: 'POST',
          // Step 23: indent_enabled（デフォルト true）を含むペイロード
          body: JSON.stringify({
            title: mockTitle,
            body: mockBody,
            platform: 'narou',
            indent_enabled: true,
          }),
        })
      );
    });
  });

  // ==========================================
  // Step 23: 字下げトグル切り替えのテスト
  // ==========================================

  it('renders indent toggle switch', () => {
    render(<PlatformCopyButton title={mockTitle} body={mockBody} />);

    // トグルスイッチ（checkbox）が存在する
    const toggle = screen.getByTestId('indent-toggle') as HTMLInputElement;
    expect(toggle).toBeInTheDocument();
    // デフォルトは字下げON（なろう推奨）
    expect(toggle.checked).toBe(true);
    expect(screen.getByText('字下げON')).toBeInTheDocument();
  });

  it('toggles indent off and sends indent_enabled false', async () => {
    const mockResponse = {
      ok: true,
      json: vi.fn().mockResolvedValue({
        title: mockTitle,
        foreword: '',
        body: '「行くぞ」\n旅人は言った。',
        afterword: '',
        total_characters: 18,
        platform: 'kakuyomu',
      }),
    };

    mockApiFetch.mockResolvedValue(mockResponse);
    mockHandleResponse.mockResolvedValue({
      title: mockTitle,
      foreword: '',
      body: '「行くぞ」\n旅人は言った。',
      afterword: '',
      total_characters: 18,
      platform: 'kakuyomu',
    });

    render(<PlatformCopyButton title={mockTitle} body={mockBody} />);

    // トグルをOFFに切り替え
    const toggle = screen.getByTestId('indent-toggle') as HTMLInputElement;
    fireEvent.click(toggle);
    expect(toggle.checked).toBe(false);
    expect(screen.getByText('字下げOFF')).toBeInTheDocument();

    // カクヨムボタンでコピー → indent_enabled: false が送信される
    fireEvent.click(screen.getByText('カクヨム'));

    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalledWith(
        '/api/export/copy/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            title: mockTitle,
            body: mockBody,
            platform: 'kakuyomu',
            indent_enabled: false,
          }),
        })
      );
    });
  });

  it('shows toast when toggling indent', () => {
    render(<PlatformCopyButton title={mockTitle} body={mockBody} />);

    const toggle = screen.getByTestId('indent-toggle');
    fireEvent.click(toggle);

    // トグル切り替え時にトースト通知が表示される
    expect(mockAddToast).toHaveBeenCalledWith(
      '📐 字下げなし: OFF（カクヨム推奨）',
      'info'
    );
  });

  it('copies formatted text to clipboard on success', async () => {
    const formattedBody = '　「行くぞ」\n　旅人は言った。';
    const mockResponse = {
      ok: true,
      json: vi.fn().mockResolvedValue({
        title: mockTitle,
        foreword: '',
        body: formattedBody,
        afterword: '',
        total_characters: 20,
        platform: 'narou',
      }),
    };

    mockApiFetch.mockResolvedValue(mockResponse);
    mockHandleResponse.mockResolvedValue({
      title: mockTitle,
      foreword: '',
      body: formattedBody,
      afterword: '',
      total_characters: 20,
      platform: 'narou',
    });

    render(<PlatformCopyButton title={mockTitle} body={mockBody} />);

    fireEvent.click(screen.getByText('なろう'));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(formattedBody);
    });
  });

  it('shows success toast on copy', async () => {
    const mockResponse = {
      ok: true,
      json: vi.fn().mockResolvedValue({
        title: mockTitle,
        foreword: '',
        body: 'formatted',
        afterword: '',
        total_characters: 10,
        platform: 'kakuyomu',
      }),
    };

    mockApiFetch.mockResolvedValue(mockResponse);
    mockHandleResponse.mockResolvedValue({
      title: mockTitle,
      foreword: '',
      body: 'formatted',
      afterword: '',
      total_characters: 10,
      platform: 'kakuyomu',
    });

    render(<PlatformCopyButton title={mockTitle} body={mockBody} />);

    fireEvent.click(screen.getByText('カクヨム'));

    await waitFor(() => {
      expect(mockAddToast).toHaveBeenCalledWith(
        '✨ カクヨム形式でコピーしました',
        'success'
      );
    });
  });

  it('falls back to raw text copy on API error', async () => {
    mockApiFetch.mockRejectedValue(new Error('Network error'));

    render(<PlatformCopyButton title={mockTitle} body={mockBody} />);

    fireEvent.click(screen.getByText('なろう'));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockBody);
      expect(mockAddToast).toHaveBeenCalledWith(
        '⚠️ 整形に失敗しました。生テキストをコピーしました。',
        'error'
      );
    });
  });

  it('shows copied state with animation', async () => {
    const mockResponse = {
      ok: true,
      json: vi.fn().mockResolvedValue({
        title: mockTitle,
        foreword: '',
        body: 'formatted',
        afterword: '',
        total_characters: 10,
        platform: 'alphapolis',
      }),
    };

    mockApiFetch.mockResolvedValue(mockResponse);
    mockHandleResponse.mockResolvedValue({
      title: mockTitle,
      foreword: '',
      body: 'formatted',
      afterword: '',
      total_characters: 10,
      platform: 'alphapolis',
    });

    render(<PlatformCopyButton title={mockTitle} body={mockBody} />);

    const alphapolisBtn = screen.getByText('アルファ');
    fireEvent.click(alphapolisBtn);

    await waitFor(() => {
      expect(alphapolisBtn).toHaveTextContent('✓ コピー済');
      expect(alphapolisBtn).toHaveClass('animate-pulse');
    });
  });

  it('handles empty text gracefully', async () => {
    const mockResponse = {
      ok: true,
      json: vi.fn().mockResolvedValue({
        title: '',
        foreword: '',
        body: '',
        afterword: '',
        total_characters: 0,
        platform: 'narou',
      }),
    };

    mockApiFetch.mockResolvedValue(mockResponse);
    mockHandleResponse.mockResolvedValue({
      title: '',
      foreword: '',
      body: '',
      afterword: '',
      total_characters: 0,
      platform: 'narou',
    });

    render(<PlatformCopyButton title="" body="" />);

    fireEvent.click(screen.getByText('なろう'));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('');
    });
  });

  it('handles special characters in text', async () => {
    const specialBody = '特殊記号: !@#$%^&*()\n絵文字: 😀🎉\nルビ: |漢字《かんじ》';
    const mockResponse = {
      ok: true,
      json: vi.fn().mockResolvedValue({
        title: mockTitle,
        foreword: '',
        body: specialBody,
        afterword: '',
        total_characters: specialBody.length,
        platform: 'narou',
      }),
    };

    mockApiFetch.mockResolvedValue(mockResponse);
    mockHandleResponse.mockResolvedValue({
      title: mockTitle,
      foreword: '',
      body: specialBody,
      afterword: '',
      total_characters: specialBody.length,
      platform: 'narou',
    });

    render(<PlatformCopyButton title={mockTitle} body={specialBody} />);

    fireEvent.click(screen.getByText('なろう'));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(specialBody);
    });
  });
});
