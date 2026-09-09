import { apiFetch } from "./client";
import { BookItem, CreateBookInput } from "../types";

const BASE_URL = "/api/books";

export async function fetchBooks(): Promise<BookItem[]> {
  const res = await apiFetch(BASE_URL);
  if (!res.ok) throw new Error("Failed to fetch books");
  return res.json();
}

export async function fetchBookById(id: number): Promise<BookItem> {
  const res = await apiFetch(`${BASE_URL}/${id}`);
  if (!res.ok) throw new Error("Failed to fetch book");
  return res.json();
}

export async function createBook(payload: CreateBookInput): Promise<BookItem> {
  const res = await apiFetch(BASE_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to create book");
  return res.json();
}

export async function deleteBook(id: number): Promise<void> {
  const res = await apiFetch(`${BASE_URL}/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete book");
}