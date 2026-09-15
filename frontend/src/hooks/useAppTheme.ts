import { useEffect, useState } from "react";

export type AppTheme = "dark" | "light" | "sepia";

const THEME_STORAGE_KEY = "autonovel.appTheme";

/**
 * 提案8: アプリ全体のテーマ（ライト/ダーク/セピア）を管理するフック。
 *
 * - localStorage 永続化（autonovel.* キー規約に準拠）
 * - 初回は prefers-color-scheme を初期値に反映
 * - data-theme 属性を <html> に設定し、CSS 変数を切り替え
 */
export function useAppTheme(): {
  theme: AppTheme;
  setTheme: (theme: AppTheme) => void;
} {
  const [theme, setThemeState] = useState<AppTheme>(() => {
    if (typeof window === "undefined") return "dark";
    try {
      const saved = localStorage.getItem(THEME_STORAGE_KEY);
      if (saved === "dark" || saved === "light" || saved === "sepia") {
        return saved;
      }
      // 保存値がない場合は OS のカラースキーム設定を尊重
      if (window.matchMedia?.("(prefers-color-scheme: light)").matches) {
        return "light";
      }
    } catch {
      // localStorage が使れない環境ではダーク固定
    }
    return "dark";
  });

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // ignore storage error
    }
  }, [theme]);

  const setTheme = (next: AppTheme) => setThemeState(next);

  return { theme, setTheme };
}

export default useAppTheme;
