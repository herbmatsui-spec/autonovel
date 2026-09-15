import { useState, useEffect } from "react";
import { EditorSnapshot } from "../types/editorSnapshot";
import { indexedDbClient } from "../lib/storage/indexedDbClient";

export function useCrashRecovery(
  bookId: string | number,
  episodeId: string | number,
  serverContent: string
) {
  const [recoverySnapshot, setRecoverySnapshot] = useState<EditorSnapshot | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    async function checkRecovery() {
      try {
        const snapshot = await indexedDbClient.getSnapshot(bookId, episodeId);
        if (!snapshot || !isMounted) return;

        // サーバーとローカルで内容が異なり、ローカルに有意な文字数がある場合に復元確認
        if (snapshot.content && snapshot.content !== serverContent && snapshot.content.length > 5) {
          setRecoverySnapshot(snapshot);
          setIsOpen(true);
        }
      } catch (e) {
        console.warn("Crash recovery check failed:", e);
      }
    }
    checkRecovery();
    return () => {
      isMounted = false;
    };
  }, [bookId, episodeId, serverContent]);

  const dismiss = () => setIsOpen(false);

  return { isOpen, recoverySnapshot, dismiss };
}