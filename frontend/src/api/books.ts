import { apiFetch, handleResponse } from "./client";
import { BookItem, CreateBookInput } from "../types";

const BASE_URL = "/api/books";

export async function fetchBooks(): Promise<BookItem[]> {
  const res = await apiFetch(BASE_URL);
  return handleResponse<BookItem[]>(res, "Failed to fetch books");
}

export async function fetchBookById(id: number): Promise<BookItem> {
  const res = await apiFetch(`${BASE_URL}/${id}`);
  return handleResponse<BookItem>(res, "Failed to fetch book");
}

export async function createBook(payload: CreateBookInput): Promise<BookItem> {
  const res = await apiFetch(BASE_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse<BookItem>(res, "Failed to create book");
}

export async function deleteBook(id: number): Promise<void> {
  const res = await apiFetch(`${BASE_URL}/${id}`, { method: "DELETE" });
  await handleResponse<void>(res, "Failed to delete book");
}