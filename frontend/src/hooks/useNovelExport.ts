import { useState, useCallback } from "react";
import { exportPackage } from "../api/easyMode";

export function useNovelExport(
  onSuccess?: (msg: string) => void,
  onError?: (msg: string) => void
) {
  const [exporting, setExporting] = useState(false);

  const downloadExportPackage = useCallback(
    async (bookId: number) => {
      setExporting(true);
      try {
        const { zipBlob, filename } = await exportPackage(bookId);
        const url = window.URL.createObjectURL(zipBlob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);

        onSuccess?.(`📦 納品パッケージ (${filename}) をダウンロードしました！`);
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "不明なエラーが発生しました";
        onError?.(`❌ ダウンロードエラー: ${msg}`);
      } finally {
        setExporting(false);
      }
    },
    [onSuccess, onError]
  );

  return { exporting, downloadExportPackage };
}
