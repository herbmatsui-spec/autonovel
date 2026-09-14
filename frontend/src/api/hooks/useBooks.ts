import { useQuery } from "@tanstack/react-query";
import { apiFetch, handleResponse } from "../client";
import type { paths } from "../../types/api.generated";

// /api/books のレスポンス型を自動生成型から抽出
type BooksResponse = paths["/api/books"]["get"]["responses"]["200"]["content"]["application/json"];

export function useBooks() {
  return useQuery<BooksResponse>({
    queryKey: ["books"],
    queryFn: async () => {
      const res = await apiFetch("/api/books");
      return handleResponse<BooksResponse>(res);
    },
  });
}
