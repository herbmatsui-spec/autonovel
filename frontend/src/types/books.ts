export interface BookItem {
  id: number;
  title: string;
  genre: string;
  concept: string;
  synopsis: string;
  target_eps: number;
  created_at: string;
}

export interface CreateBookInput {
  title: string;
  genre: string;
  concept: string;
  synopsis: string;
  target_eps: number;
}