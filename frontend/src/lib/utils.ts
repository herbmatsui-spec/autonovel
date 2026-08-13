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
