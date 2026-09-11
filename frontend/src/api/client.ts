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

export class ApiError extends Error {
  status: number;
  data?: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export async function extractErrorMessage(res: Response): Promise<string> {
  try {
    const clone = res.clone();
    const data = await clone.json();
    if (typeof data === "string") return data;
    if (data?.detail) {
      if (typeof data.detail === "string") return data.detail;
      if (Array.isArray(data.detail)) {
        return data.detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ");
      }
      return JSON.stringify(data.detail);
    }
    if (data?.error_message) return data.error_message;
    if (data?.message) return data.message;
    return JSON.stringify(data);
  } catch {
    return res.statusText || `HTTP error ${res.status}`;
  }
}

export async function handleResponse<T>(
  res: Response,
  defaultErrorMsg = "API request failed"
): Promise<T> {
  if (!res.ok) {
    const errorDetail = await extractErrorMessage(res);
    let msg = `${defaultErrorMsg}: ${errorDetail}`;
    if (res.status === 401) {
      msg = `[401 認証エラー] APIキーが設定されていないか無効です: ${errorDetail}`;
    } else if (res.status === 403) {
      msg = `[403 権限エラー] アクセスが拒否されました: ${errorDetail}`;
    }
    throw new ApiError(msg, res.status);
  }
  return res.json();
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
