# SSE ストリーミング生成 — 移行ガイド

## 変更点

- 旧: `POST /easy_mode/generate/stream` (廃止予定)
- 新: `GET  /easy_mode/generate/stream` (EventSource 互換)

ブラウザの `EventSource` は `GET` のみ対応しているため、POST エンドポイントは
`deprecated` 化され、将来的に削除されます。

## フロントエンド実装例

```typescript
// 1. 個別クエリパラメータで送信
const qs = new URLSearchParams({
  current_chapter: text,
  character_name: name,
  character_personality: personality,
  character_ability: ability,
  character_genre: genre,
  content_length_limit: "2000",
}).toString();
const es = new EventSource(`/easy_mode/generate/stream?${qs}`);

es.addEventListener("message", (ev) => {
  const data = JSON.parse(ev.data);
  if (data.type === "chunk") append(data.text);
  if (data.type === "done") { es.close(); }
  if (data.type === "error") { es.close(); console.error(data.message); }
});

// 2. base64 payload で送信 (大きな入力を安全に)
const payload = btoa(JSON.stringify(input));
const es2 = new EventSource(`/easy_mode/generate/stream?payload=${encodeURIComponent(payload)}`);
```

## イベントタイプ

| type    | 内容                          |
|---------|-------------------------------|
| start   | ストリーム開始 (1 回)         |
| chunk   | テキストチャンク (複数回)     |
| done    | 正常終了 (1 回)               |
| error   | 異常終了 (1 回, メッセージ)   |

## レート制限

- `stream_limiter`: 3 req / 60 sec / IP
- 制限超過時は HTTP 429 を返す (SSE 接続確立前)
