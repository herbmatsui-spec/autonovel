import { useEffect } from "react";

/**
 * 提案7: 長時間生成（AI執筆など）中のページ離脱を警告するフック。
 *
 * isBusy === true の間、beforeunload でブラウザ標準の確認ダイアログを表示し、
 * 誤操作による生成中断を防止する。
 */
export function useUnsavedGenerationGuard(isBusy: boolean): void {
  useEffect(() => {
    if (!isBusy) return;

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      // Chrome では returnValue の設定が必須
      e.preventDefault();
      e.returnValue = "生成中のタスクがあります。このページを離れますか？";
      return e.returnValue;
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isBusy]);
}

export default useUnsavedGenerationGuard;
