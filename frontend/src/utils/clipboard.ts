export async function copyWithFallback(
  text: string,
  fallbackBlob?: Blob
): Promise<{ success: boolean; usedFallback: boolean }> {
  try {
    await navigator.clipboard.writeText(text);
    return { success: true, usedFallback: false };
  } catch {
    if (fallbackBlob) {
      const url = URL.createObjectURL(fallbackBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'export.txt';
      a.click();
      URL.revokeObjectURL(url);
      return { success: true, usedFallback: true };
    }
    // textarea フォールバック
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
    return { success: true, usedFallback: true };
  }
}