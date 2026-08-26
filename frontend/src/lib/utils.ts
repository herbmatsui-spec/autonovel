import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * 未知のエラー (unknown) から安全にメッセージ文字列を取り出す。
 * catch (e: unknown) ブロック内で使うことを想定。
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === "string") return error
  return "不明なエラーが発生しました。"
}

/**
 * URLが同一オリジンまたは相対パスかどうかをチェックし、オープンリダイレクトを防止する
 * @param url チェック対象のURL
 * @returns 同一オリジンまたは相対パスの場合true
 */
export function isSafeRedirect(url: string): boolean {
  try {
    // 絶対URLの場合
    const urlObj = new URL(url, window.location.origin)
    return urlObj.origin === window.location.origin
  } catch {
    // 相対URLの場合（例: "/path" または "path"）
    // ただし "//" で始まるものはプロトコル相対URLとして扱わず拒否
    return url.startsWith('/') && !url.startsWith('//')
  }
}