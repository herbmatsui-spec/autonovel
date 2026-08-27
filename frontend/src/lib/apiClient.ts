/**
 * apiClient.ts - 統一 API クライアント
 * 
 * すべての API リクエスト（api.ts, easyModeApi.ts 等）で共通の
 * ベースURL解決、X-API-Key 認証ヘッダー付与、JSONパース、エラーハンドリングを提供します。
 */

export interface RequestOptions extends RequestInit {
  apiKey?: string;
  params?: Record<string, string | number | boolean | undefined>;
}

// safely access import.meta.env for Vite environment variables
const VITE_API_URL = (import.meta as unknown as { env?: { VITE_API_URL?: string } })?.env?.VITE_API_URL;
export const API_BASE_URL = VITE_API_URL || '/api';

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * 汎用 API リクエスト関数
 */
export async function request<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { apiKey, params, headers: customHeaders, ...restOptions } = options;

  // URL 構築
  let url: string;
  if (endpoint.startsWith('http')) {
    url = endpoint;
  } else if (endpoint.startsWith(API_BASE_URL)) {
    url = endpoint;
  } else {
    url = `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
  }

  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes('?') ? '&' : '?') + queryString;
    }
  }

  // ヘッダー構築
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(customHeaders as Record<string, string> || {}),
  };

  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  const response = await fetch(url, {
    credentials: 'include',
    headers,
    ...restOptions,
  });

  if (!response.ok) {
    let errorDetail = `API Error (${response.status})`;
    let errorData: unknown = null;
    try {
      errorData = await response.json();
      if (errorData && typeof errorData === 'object') {
        const d = errorData as Record<string, unknown>;
        if (typeof d.detail === 'string') {
          errorDetail = d.detail;
        } else if (typeof d.error_message === 'string') {
          errorDetail = d.error_message;
        } else if (typeof d.error === 'string') {
          errorDetail = d.error;
        }
      }
    } catch {
      try {
        errorDetail = await response.text();
      } catch {
        // use default
      }
    }
    throw new ApiError(response.status, errorDetail, errorData);
  }

  // 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

/**
 * レスポンス状態管理ラッパー（後方互換）
 */
export interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  isLoading: boolean;
}

export async function apiClient<T>(
  apiCall: () => Promise<T>
): Promise<{ data: T | null; error: string | null; isLoading: boolean }> {
  let isLoading = true;
  let data = null as T | null;
  let error = null as string | null;

  try {
    data = await apiCall();
  } catch (e: unknown) {
    error = e instanceof Error ? e.message : "An unexpected error occurred";
  } finally {
    isLoading = false;
  }

  return { data, error, isLoading };
}

export function createAsyncState<T>() {
  return {
    data: null as T | null,
    error: null as string | null,
    isLoading: false,
  };
}
