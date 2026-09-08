/**
 * frontend/src/api/client.ts - 共通 API クライアント層
 *
 * 各 API リクエスト時に LocalStorage から API キーを取得し、
 * X-API-Key ヘッダーを自動付与して fetch を実行する。
 */

export function getApiKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("autonovel_api_key") || "";
}

export function setApiKey(key: string): void {
  if (typeof window === "undefined") return;
  if (key) {
    localStorage.setItem("autonovel_api_key", key);
  } else {
    localStorage.removeItem("autonovel_api_key");
  }
}

export async function apiFetch(
  input: RequestInfo | URL,
  init: RequestInit = {}
): Promise<Response> {
  const headers = new Headers(init.headers || {});
  const apiKey = getApiKey();
  if (apiKey && !headers.has("X-API-Key")) {
    headers.set("X-API-Key", apiKey);
  }
  return fetch(input, { ...init, headers });
}
