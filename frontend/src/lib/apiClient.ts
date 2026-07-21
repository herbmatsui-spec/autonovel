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
  } catch (e: any) {
    error = e instanceof Error ? e.message : "An unexpected error occurred";
  } finally {
    isLoading = false;
  }

  return { data, error, isLoading };
}

// Helper for useAsync hook to maintain state
export function createAsyncState() {
  return {
    data: null as any,
    error: null as string | null,
    isLoading: false,
  };
}
