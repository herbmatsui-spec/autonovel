import { useState } from 'react';

export function usePagination(totalItems: number, itemsPerPage: number = 5) {
  const [page, setPage] = useState(1);
  const totalPages = Math.max(1, Math.ceil(totalItems / itemsPerPage));
  const startIdx = (page - 1) * itemsPerPage;
  const endIdx = startIdx + itemsPerPage;
  const paginatedItems = (items: any[]) => items.slice(startIdx, endIdx);
  return { page, setPage, totalPages, paginatedItems };
}
