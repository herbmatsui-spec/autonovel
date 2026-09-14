/**
 * 型安全 API クライアント基盤
 */
export async function apiFetch(
  endpoint: string,
  options?: RequestInit
): Promise<Response> {
  const token = localStorage.getItem("auth_token");
  const headers = new Headers(options?.headers || {});
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  return response;
}

export async function handleResponse<T>(response: Response, errorMessage?: string): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw errorData;
  }
  return response.json() as Promise<T>;
}
