import { copyWithFallback } from '@/utils/clipboard';

describe('copyWithFallback', () => {
  const testText = 'Hello, world!';
  const testBlob = new Blob(['test'], { type: 'text/plain' });

  beforeEach(() => {
    // navigator.clipboard をモック
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: vi.fn(),
      },
      writable: true,
    });
    
    // document.execCommand をモック
    document.execCommand = vi.fn().mockReturnValue(true);
    
    // URL.createObjectURL と URL.revokeObjectURL をモック
    URL.createObjectURL = vi.fn();
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  test('navigator.clipboard.writeText 成功 → {success:true, usedFallback:false}', async () => {
    (navigator.clipboard.writeText as vi.Mock).mockResolvedValue(undefined);

    const result = await copyWithFallback(testText);

    expect(result).toEqual({ success: true, usedFallback: false });
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(testText);
  });

  test('writeText 失敗 + fallbackBlob あり → ダウンロード発火・{success:true, usedFallback:true}', async () => {
    (navigator.clipboard.writeText as vi.Mock).mockRejectedValue(new Error('Clipboard write failed'));
    // URL.createObjectURL をモックして偽のURLを返す
    const fakeUrl = 'fake-url';
    URL.createObjectURL.mockReturnValue(fakeUrl);

    const result = await copyWithFallback(testText, testBlob);

    expect(result).toEqual({ success: true, usedFallback: true });
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(testText);
    // document.execCommand should not be called when fallbackBlob is provided
    expect(document.execCommand).not.toHaveBeenCalled();
    // URL.createObjectURL と URL.revokeObjectURL が呼ばれることを確認
    expect(URL.createObjectURL).toHaveBeenCalledWith(testBlob);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith(fakeUrl);
  });

  test('writeText 失敗 + fallbackBlob なし → execCommand("copy") 呼び出し・{success:true, usedFallback:true}', async () => {
    (navigator.clipboard.writeText as vi.Mock).mockRejectedValue(new Error('Clipboard write failed'));

    const result = await copyWithFallback(testText);

    expect(result).toEqual({ success: true, usedFallback: true });
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(testText);
    expect(document.execCommand).toHaveBeenCalledWith('copy');
  });

  test('execCommand も失敗 → {success:false, usedFallback:true}', async () => {
    (navigator.clipboard.writeText as vi.Mock).mockRejectedValue(new Error('Clipboard write failed'));
    document.execCommand.mockReturnValueOnce(false);

    const result = await copyWithFallback(testText);

    expect(result).toEqual({ success: false, usedFallback: true });
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(testText);
    expect(document.execCommand).toHaveBeenCalledWith('copy');
  });
});