# ハイブリッド共同編集 実装計画書（Option 3）

**目標**: 既存の REST + SSE インフラを活用し、ローカルファースト・定期同期・手動競合解決で MVP を 12 ステップで構築  
**前提**: 低性能 LLM でも 1 ステップずつ確実に実装できる粒度・自己完結性・テスト容易性を重視

---

## Step 1: バックエンド - バージョンログ テーブル追加

**ファイル**: `src/backend/database/models.py`  
**作業**: `ChapterVersion` モデルを追加（マイグレーション不要なら `create_all` で自動生成）

```python
class ChapterVersion(Base):
    __tablename__ = "chapter_versions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    chapter_ep = Column(Integer, nullable=False)
    user_name = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)          # 完全本文スナップショット
    vector_clock = Column(JSON, nullable=False)     # {"userA": 3, "userB": 1}
    base_version_id = Column(Integer, ForeignKey("chapter_versions.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_chv_book_chap", "book_id", "chapter_ep"),)
```

**確認**: `alembic revision --autogenerate -m "add chapter_versions"` → `alembic upgrade head` 成功

---

## Step 2: バックエンド - リポジトリにバージョン操作追加

**ファイル**: `src/backend/database/repositories/collab.py`  
**追加メソッド**:

```python
async def save_version(self, book_id: int, chapter_ep: int, user_name: str,
                       content: str, vector_clock: dict, base_version_id: int | None) -> int:
    v = ChapterVersion(book_id=book_id, chapter_ep=chapter_ep,
                       user_name=user_name, content=content,
                       vector_clock=vector_clock, base_version_id=base_version_id)
    self.session.add(v)
    await self.session.flush()
    return v.id

async def get_latest_version(self, book_id: int, chapter_ep: int) -> ChapterVersion | None:
    stmt = (select(ChapterVersion)
            .where(ChapterVersion.book_id == book_id, ChapterVersion.chapter_ep == chapter_ep)
            .order_by(ChapterVersion.id.desc()).limit(1))
    return (await self.session.execute(stmt)).scalar_one_or_none()

async def get_version(self, version_id: int) -> ChapterVersion | None:
    return await self.session.get(ChapterVersion, version_id)
```

**単体テスト**: `tests/unit/test_collab_repo.py` で CRUD 確認

---

## Step 3: バックエンド - ルーターに同期エンドポイント追加

**ファイル**: `src/backend/routers/collab.py`  
**追加エンドポイント**:

```python
class SyncRequest(BaseModel):
    user_name: str
    content: str
    vector_clock: dict[str, int]      # クライアント側ベクトルクロック
    base_version_id: int | None       # 最後に既知のサーババージョン ID

class SyncResponse(BaseModel):
    status: Literal["synced", "conflict"]
    merged_content: str
    new_version_id: int
    server_vector_clock: dict[str, int]
    conflict_sections: list[dict] | None = None  # conflict 時のみ
```

```python
@router.post("/books/{book_id}/chapters/{chapter_ep}/sync", response_model=SyncResponse)
async def sync_chapter(book_id: int, chapter_ep: int, req: SyncRequest):
    async with UnitOfWork(AppContainer.db()) as uow:
        # 1. サーバ最新版取得
        server_ver = await uow.collab.get_latest_version(book_id, chapter_ep)
        server_vc = server_ver.vector_clock if server_ver else {}
        server_content = server_ver.content if server_ver else ""

        # 2. ベクトルクロック比較 → 競合判定
        client_vc = req.vector_clock
        is_conflict = any(client_vc.get(k, 0) < server_vc.get(k, 0) for k in server_vc)

        if not is_conflict:
            # 3a. 競合なし → クライアント版採用 + VC インクリメント
            new_vc = {**server_vc, req.user_name: client_vc.get(req.user_name, 0) + 1}
            new_ver_id = await uow.collab.save_version(
                book_id, chapter_ep, req.user_name, req.content, new_vc, server_ver.id if server_ver else None)
            await uow.commit()
            return SyncResponse(status="synced", merged_content=req.content,
                                new_version_id=new_ver_id, server_vector_clock=new_vc)

        # 3b. 競合あり → 段落単位 LWW マージ + 競合セクション返却
        merged, conflicts = merge_paragraphs_lww(server_content, req.content, server_vc, client_vc)
        new_vc = {**server_vc, req.user_name: client_vc.get(req.user_name, 0) + 1}
        new_ver_id = await uow.collab.save_version(
            book_id, chapter_ep, req.user_name, merged, new_vc, server_ver.id)
        await uow.commit()
        return SyncResponse(status="conflict", merged_content=merged,
                            new_version_id=new_ver_id, server_vector_clock=new_vc,
                            conflict_sections=conflicts)
```

**ヘルパー関数** `merge_paragraphs_lww` は同ファイル内に記述（段落 = `\n\n` 区切り、タイムスタンプで LWW、同タイムスタンプならユーザー名辞書順）

**確認**: `curl -X POST /api/collab/books/1/chapters/1/sync -d '{"user_name":"A","content":"...","vector_clock":{"A":1},"base_version_id":null}'` で 200 返却

---

## Step 4: バックエンド - プレゼンス エンドポイント追加（SSE 既存流用）

**ファイル**: `src/backend/routers/collab.py`  
**追加**:

```python
# インメモリ（本番は Redis）で十分。ユーザーごと最新プレゼンス保持
_presence: dict[tuple[int, int], dict[str, dict]] = {}  # (book_id, chap) -> {user: {cursor, selection, updated}}

@router.post("/books/{book_id}/chapters/{chapter_ep}/presence")
async def update_presence(book_id: int, chapter_ep: int,
                          payload: dict = Body(...)):  # {user_name, cursor, selection}
    _presence.setdefault((book_id, chapter_ep), {})[payload["user_name"]] = {
        "cursor": payload.get("cursor"),
        "selection": payload.get("selection"),
        "updated": datetime.utcnow().isoformat()
    }
    return {"status": "ok"}

@router.get("/books/{book_id}/chapters/{chapter_ep}/presence")
async def get_presence(book_id: int, chapter_ep: int):
    now = datetime.utcnow()
    data = _presence.get((book_id, chapter_ep), {})
    # 30秒以上更新ないユーザー除外
    return {u: p for u, p in data.items()
            if (now - datetime.fromisoformat(p["updated"])).total_seconds() < 30}
```

**確認**: 2 タブで POST/GET し合い、カーソル位置が JSON で返ること

---

## Step 5: フロントエンド - 共有フック `useCollabSync` 作成

**ファイル**: `frontend/src/hooks/useCollabSync.ts`（新規）

```typescript
export function useCollabSync(bookId: number, chapterEp: number, userName: string) {
  const [vc, setVc] = useState<Record<string, number>>({ [userName]: 0 });
  const [baseVerId, setBaseVerId] = useState<number | null>(null);
  const [conflicts, setConflicts] = useState<ConflictSection[]>([]);
  const [presence, setPresence] = useState<PresenceMap>({});

  const sync = useCallback(async (content: string) => {
    const res = await fetch(`/api/collab/books/${bookId}/chapters/${chapterEp}/sync`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_name: userName, content, vector_clock: vc, base_version_id: baseVerId })
    });
    const data = await res.json();
    setVc(data.server_vector_clock);
    setBaseVerId(data.new_version_id);
    if (data.status === "conflict") setConflicts(data.conflict_sections);
    return data.merged_content;
  }, [bookId, chapterEp, userName, vc, baseVerId]);

  // 2秒ごと自動同期
  useEffect(() => {
    const id = setInterval(() => sync(editorContentRef.current), 2000);
    return () => clearInterval(id);
  }, [sync]);

  // プレゼンス 5秒ポーリング
  useEffect(() => {
    const id = setInterval(async () => {
      const res = await fetch(`/api/collab/books/${bookId}/chapters/${chapterEp}/presence`);
      setPresence(await res.json());
    }, 5000);
    return () => clearInterval(id);
  }, [bookId, chapterEp]);

  // 自分のカーソル送信
  const sendPresence = useCallback((cursor: number, selection?: {start:number,end:number}) => {
    fetch(`/api/collab/books/${bookId}/chapters/${chapterEp}/presence`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_name: userName, cursor, selection })
    });
  }, [bookId, chapterEp, userName]);

  return { sync, conflicts, presence, sendPresence };
}
```

**確認**: Storybook または手動でフック単体動作確認

---

## Step 6: フロントエンド - `Editor` に `useCollabSync` 統合

**ファイル**: `frontend/src/components/editor/Editor.tsx`  
**変更点**:
1. `useCollabSync` を import・呼び出し
2. `onChange` 内で `sync(newContent)` 呼び出し → 戻り値で `setCurrentChapterText` 上書き（競合時はマージ済み本文が返る）
3. `onSelect` で `sendPresence(cursor, selectionRange)` 呼び出し
4. `conflicts` が空でない場合、ツールバー下に「⚠ 競合検出」バナー表示（クリックで詳細モーダル）

**確認**: 2 ブラウザで同時編集し、自動マージ・競合バナー表示を目視

---

## Step 7: フロントエンド - 競合詳細モーダル `ConflictModal` 作成

**ファイル**: `frontend/src/components/editor/ConflictModal.tsx`（新規）

```tsx
interface ConflictSection {
  index: number;           // 段落インデックス
  server_text: string;
  client_text: string;
  chosen: "server" | "client";
}

export const ConflictModal: React.FC<{
  conflicts: ConflictSection[];
  onResolve: (resolutions: Record<number, "server" | "client">) => void;
}> = ({ conflicts, onResolve }) => {
  const [choices, setChoices] = useState<Record<number, "server" | "client">>({});

  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <h3>⚠ 競合が検出されました（{conflicts.length}箇所）</h3>
        {conflicts.map(c => (
          <div key={c.index} className="conflict-block">
            <label><input type="radio" name={c.index} value="server" checked={choices[c.index]==="server"}
              onChange={() => setChoices({...choices, [c.index]:"server"})} /> サーバ版</label>
            <pre>{c.server_text}</pre>
            <label><input type="radio" name={c.index} value="client" checked={choices[c.index]==="client"}
              onChange={() => setChoices({...choices, [c.index]:"client"})} /> 自分の版</label>
            <pre>{c.client_text}</pre>
          </div>
        ))}
        <button onClick={() => onResolve(choices)}>適用して同期</button>
      </div>
    </div>
  );
};
```

**確認**: Step 6 のバナーからモーダル開き、選択後 `sync` 再実行で競消解消

---

## Step 8: フロントエンド - プレゼンス表示（他ユーザーのカーソル・選択）

**ファイル**: `frontend/src/components/editor/Editor.tsx`  
**追加**:
- `presence` から自分以外のユーザー抽出
- `textarea` と同サイズの透明 `div` を重ね、各ユーザーの `cursor` 位置に `|` カーソル画像、`selection` 範囲に半透明ハイライトを CSS で描画
- ユーザーごとに色割り当て（ハッシュから HSL 生成）

**確認**: 2 ブラウザで相手のカーソル・選択がリアルタイム風に見えること

---

## Step 9: フロントエンド - ローカル下書き自動保存・復元

**ファイル**: `frontend/src/hooks/useLocalDraft.ts`（新規）

```typescript
export function useLocalDraft(key: string, initial: string) {
  const [content, setContent] = useState(() => {
    const saved = localStorage.getItem(key);
    return saved ? JSON.parse(saved) : initial;
  });
  useEffect(() => {
    const id = setInterval(() => localStorage.setItem(key, JSON.stringify(content)), 2000);
    return () => clearInterval(id);
  }, [content, key]);
  return [content, setContent] as const;
}
```

**統合**: `Editor` 内で `useLocalDraft(`draft_${bookId}_${chapterEp}`, initialContent`)` に置換  
**確認**: ブラウザリロード後も入力中の草稿が復元されること

---

## Step 10: バックエンド - 競合マージ関数の単体テスト追加

**ファイル**: `tests/unit/test_collab_merge.py`（新規）

```python
def test_merge_no_conflict():
    assert merge_paragraphs_lww("A\n\nB", "A\n\nC", {}, {"A":1}) == ("A\n\nC", [])

def test_merge_conflict_same_paragraph():
    merged, conflicts = merge_paragraphs_lww("P1\n\nP2", "P1\n\nP2'", {"u1":1}, {"u2":1})
    assert len(conflicts) == 1
    assert conflicts[0]["index"] == 1
```

**実行**: `pytest tests/unit/test_collab_merge.py -v` 全パス

---

## Step 11: 統合テスト（E2E）

**ファイル**: `tests/integration/test_collab_hybrid.py`（新規）  
**シナリオ**:
1. ユーザー A・B 同時に同じ章を開く
2. A が段落 1 編集 → 2 秒後自動同期 → B の画面に反映
3. B が段落 2 編集 → 同期
4. A と B が**同じ段落**をほぼ同時に編集 → 競合発生 → バナー表示
5. A がモーダルで「自分の版」選択 → 再同期 → 競合解消
6. ブラウザリロード → ローカル下書き復元確認

**実行**: `pytest tests/integration/test_collab_hybrid.py -v -s`

---

## Step 12: ドキュメント・設定・クリーンアップ

1. `docs/collab-hybrid-usage.md` 作成（ユーザー向け使い方・制限事項）
2. `.env.example` に `COLLAB_PRESENCE_TTL=30` 追加（将来 Redis 移行用）
3. 未使用 import・デバッグ log 削除
4. `ruff check . && mypy src/backend` パス確認
5. `npm run lint && npm run typecheck` パス確認
6. 完了報告

---

## 依存関係グラフ（並行可否）

```
Step 1 → Step 2 → Step 3 → Step 10
                      ↘
Step 4 ──────────────→ Step 5 → Step 6 → Step 7 → Step 8
                      ↘
Step 9 ──────────────────────────────────────────────→ Step 6
                                                    ↘
Step 11 ←────────────────────────────────────────── Step 6-10 完了後
                                                    ↘
Step 12 ←──────────────────────────────────────────── Step 11 完了後
```

**並行推奨**: Step 4 と Step 9 は独立して実装可能。Step 1-3 は順序厳守。

---

## 完了基準（Definition of Done）

- [ ] 2 ブラウザで同時編集し、自動マージ・競合検出・手動解決・プレゼンス表示・リロード復元がすべて手動確認済み
- [ ] 単体・統合テストすべてパス
- [ ] リンター・型チェック・ビルドエラー 0
- [ ] ドキュメント更新済み