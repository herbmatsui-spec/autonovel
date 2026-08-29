import { useState, useCallback } from 'react';
import { useBookStore } from '@/store/useBookStore';

const WORKSPACE_FILES = [
  'SOUL.md',
  'WORLD.md',
  'CHARACTERS.md',
  'OUTLINE.md',
  'STORY_SUMMARY.md',
  'MEMORY.md',
];

export function useWorkspaceFiles() {
  const { selectedBook } = useBookStore();
  const [files, setFiles] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    if (!selectedBook) return;
    setLoading(true);
    setError(null);
    try {
      const results = await Promise.all(
        WORKSPACE_FILES.map((fname) =>
          fetch(`/api/workspace/${selectedBook.id}/files/${fname}`).then((r) =>
            r.json().then((d) => ({ filename: fname, content: d.content || '' }))
          )
        )
      );
      setFiles(Object.fromEntries(results.map((r) => [r.filename, r.content])));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [selectedBook]);

  const saveFile = useCallback(async (filename: string, content: string) => {
    if (!selectedBook) return;
    try {
      await fetch(`/api/workspace/${selectedBook.id}/files/${filename}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      setFiles((prev) => ({ ...prev, [filename]: content }));
    } catch (e: any) {
      setError(e.message);
    }
  }, [selectedBook]);

  return { files, loading, error, loadAll, saveFile };
}