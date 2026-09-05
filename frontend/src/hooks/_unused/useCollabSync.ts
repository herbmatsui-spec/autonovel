import { useState, useCallback, useEffect, useRef } from "react";

export interface ConflictSection {
  index: number;
  server_text: string;
  client_text: string;
}

export interface PresenceInfo {
  cursor: number | null;
  selection: { start: number; end: number } | null;
  updated: string;
}

export interface PresenceMap {
  [userName: string]: PresenceInfo;
}

export interface SyncResult {
  mergedContent: string;
  serverVectorClock: Record<string, number>;
  newVersionId: number;
  status: "synced" | "conflict";
  conflicts: ConflictSection[];
}

export function useCollabSync(
  bookId: number,
  chapterEp: number,
  userName: string,
  initialContent: string
) {
  const [vc, setVc] = useState<Record<string, number>>({ [userName]: 0 });
  const [baseVerId, setBaseVerId] = useState<number | null>(null);
  const [conflicts, setConflicts] = useState<ConflictSection[]>([]);
  const [presence, setPresence] = useState<PresenceMap>({});
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncedContent, setLastSyncedContent] = useState(initialContent);

  const editorContentRef = useRef(initialContent);
  editorContentRef.current = initialContent;

  const sync = useCallback(
    async (content: string): Promise<SyncResult> => {
      setIsSyncing(true);
      try {
        const res = await fetch(
          `/api/collab/books/${bookId}/chapters/${chapterEp}/sync`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              user_name: userName,
              content,
              vector_clock: vc,
              base_version_id: baseVerId,
            }),
          }
        );
        const data = await res.json();
        setVc(data.server_vector_clock);
        setBaseVerId(data.new_version_id);
        if (data.status === "conflict") {
          setConflicts(data.conflict_sections || []);
        } else {
          setConflicts([]);
        }
        setLastSyncedContent(data.merged_content);
        return {
          mergedContent: data.merged_content,
          serverVectorClock: data.server_vector_clock,
          newVersionId: data.new_version_id,
          status: data.status,
          conflicts: data.conflict_sections || [],
        };
      } finally {
        setIsSyncing(false);
      }
    },
    [bookId, chapterEp, userName, vc, baseVerId]
  );

  // 2秒ごと自動同期
  useEffect(() => {
    const id = setInterval(() => {
      const currentContent = editorContentRef.current;
      if (currentContent !== lastSyncedContent) {
        sync(currentContent);
      }
    }, 2000);
    return () => clearInterval(id);
  }, [sync, lastSyncedContent]);

  // プレゼンス 5秒ポーリング
  useEffect(() => {
    const fetchPresence = async () => {
      try {
        const res = await fetch(
          `/api/collab/books/${bookId}/chapters/${chapterEp}/presence`
        );
        setPresence(await res.json());
      } catch {
        // ignore
      }
    };
    fetchPresence();
    const id = setInterval(fetchPresence, 5000);
    return () => clearInterval(id);
  }, [bookId, chapterEp]);

  // 自分のカーソル送信
  const sendPresence = useCallback(
    (cursor: number | null, selection?: { start: number; end: number } | null) => {
      fetch(`/api/collab/books/${bookId}/chapters/${chapterEp}/presence`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_name: userName, cursor, selection }),
      }).catch(() => {});
    },
    [bookId, chapterEp, userName]
  );

  // 強制同期（保存ボタン等から呼ぶ用）
  const forceSync = useCallback(async () => {
    return sync(editorContentRef.current);
  }, [sync]);

  return {
    sync,
    forceSync,
    conflicts,
    presence,
    sendPresence,
    isSyncing,
    vectorClock: vc,
    baseVersionId: baseVerId,
    lastSyncedContent,
  };
}