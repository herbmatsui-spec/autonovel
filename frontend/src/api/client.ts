/**
 * 型安全 API クライアント基盤
 *
 * 提案6: エラーUX改善
 * - AbortController によるタイムアウト（デフォルト 30 秒）
 * - ネットワーク断（fetch 自体の失敗）とHTTPエラーの区別
 * - 401 時の auth_token 除去（ログアウト連携）
 */

export const DEFAULT_API_TIMEOUT_MS = 30_000;

export class ApiNetworkError extends Error {
  constructor(message = "ネットワークに接続できません。接続を確認してください。") {
    super(message);
    this.name = "ApiNetworkError";
  }
}

export class ApiTimeoutError extends Error {
  constructor(timeoutMs: number) {
    super(`リクエストがタイムアウトしました（${Math.round(timeoutMs / 1000)}秒）。しばらくしてから再試行してください。`);
    this.name = "ApiTimeoutError";
  }
}

export async function apiFetch(
  endpoint: string,
  options?: RequestInit,
  timeoutMs: number = DEFAULT_API_TIMEOUT_MS
): Promise<Response> {
  const token = localStorage.getItem("auth_token");
  const headers = new Headers(options?.headers || {});
  if (!headers.has("Content-Type") && options?.body) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(endpoint, {
      ...options,
      headers,
      signal: options?.signal ?? controller.signal,
    });
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    // AbortError: タイムアウト or 呼び出し側の中断
    if (err instanceof DOMException && err.name === "AbortError") {
      if (options?.signal?.aborted) {
        throw err; // 呼び出し側の意図的な中断はそのまま伝播
      }
      throw new ApiTimeoutError(timeoutMs);
    }
    // fetch 自体の失敗（オフライン・DNS 失敗など）
    throw new ApiNetworkError();
  }
  clearTimeout(timeoutId);

  // 401: 認証切れ → トークンを除去（AuthContext が次回未認証扱いにする）
  if (response.status === 401) {
    try {
      localStorage.removeItem("auth_token");
    } catch {
      // ignore storage error
    }
  }

  return response;
}

export async function handleResponse<T>(response: Response, errorMessage?: string): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    if (errorMessage && !("detail" in errorData) && !("title" in errorData)) {
      throw { detail: errorMessage, ...errorData };
    }
    throw errorData;
  }
  return response.json() as Promise<T>;
}
