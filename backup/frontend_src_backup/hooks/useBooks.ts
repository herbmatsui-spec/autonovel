import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { getBooks, deleteBook, Book } from '../api';
import { apiClient } from '../lib/apiClient';

export function useBooks() {
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBooksList = async () => {
    setLoading(true);
    const { data, error: apiError } = await apiClient(() => getBooks());
    
    if (apiError) {
      setError('バックエンドAPIの接続に失敗しました。サーバーが起動しているか確認してください。');
    } else if (data) {
      setBooks(data);
      setError(null);
    }
    setLoading(false);
  };

  const handleDeleteBook = async (id: number) => {
    if (!window.confirm('この作品データを削除しますか？データベース内のチャプターとプロットが消去されます。')) return;
    
    const previousBooks = [...books];
    setBooks(books.filter(b => b.id !== id));

    try {
      await deleteBook(id);
      toast.success('作品を削除しました');
    } catch (err: any) {
      setBooks(previousBooks);
      toast.error('作品の削除に失敗しました: ' + err.message);
    }
  };

  useEffect(() => {
    fetchBooksList();
  }, []);

  return {
    books,
    loading,
    error,
    fetchBooksList,
    handleDeleteBook
  };
}
