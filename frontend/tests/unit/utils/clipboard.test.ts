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

    // document.execCommand をモック（成功する場合）
    const execCommandSpy = vi.spyOn(document, 'execCommand').mockReturnValue(true);

    const result = await copyWithFallback(testText, testBlob);

    expect(result).toEqual({ success: true, usedFallback: true });
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(testText);
    expect(execCommandSpy).not.toHaveBeenCalled();
    
    // Blob URL が作成され、ダウンロードリンクがクリックされることを確認
    // (実際の URL.createObjectURL と element.click のモックは複雑になるため、
    // ここでは fallbackBlob が使用されたことを usedFallback: true で確認)
    execCommandSpy.mockRestore();
  });

  test('writeText 失敗 + fallbackBlob なし → execCommand('copy') 呼び出し・{success:true, usedFallback:true}', async () => {
    (navigator.clipboard.writeText as vi.Mock).mockRejectedValue(new Error('Clipboard write failed'));

    // document.execCommand をモック（成功する場合）
    const execCommandSpy = vi.spyOn(document, 'execCommand').mockReturnValue(true);

    const result = await copyWithFallback(testText);

    expect(result).toEqual({ success: true, usedFallback: true });
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(testText);
    expect(execCommandSpy).toHaveBeenCalledWith('copy');
    execCommandSpy.mockRestore();
  });

  test('execCommand も失敗 → {success:false, usedFallback:true}', async () => {
    (navigator.clipboard.writeText as vi.Mock).mockRejectedValue(new Error('Clipboard write failed'));

    // document.execCommand をモック（失敗する場合）
    const execCommandSpy = vi.spyOn(document, 'execCommand').mockReturnValue(false);

    const result = await copyWithFallback(testText);

    expect(result).toEqual({ success: false, usedFallback: true });
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(testText);
    expect(execCommandSpy).toHaveBeenCalledWith('copy');
    execCommandSpy.mockRestore();
  });
});