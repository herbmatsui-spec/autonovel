/**
 * 上級者エディタ（Studio Mode）API クライアント
 */
import {
  AssistRequest,
  AssistResponse,
  AskBibleRequest,
  AskBibleResponse,
  ConsistencyAuditRequest,
  ConsistencyAuditResponse,
  NextBeatsRequest,
  NextBeatsResponse,
} from "../types/editor";

const BASE = "/api/editor";

/**
 * エラーハンドリング用ヘルパー
 */
async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status} ${res.statusText}`;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.error || errorDetail;
    } catch {
      const text = await res.text();
      if (text) errorDetail = text;
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

/**
 * インライン AI アシスト（五感描写拡張・Show Don't Tell・トーン書き換え）
 */
export async function assistContent(input: AssistRequest): Promise<AssistResponse> {
  const res = await fetch(`${BASE}/assist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleResponse<AssistResponse>(res);
}

/**
 * GraphRAG 専属 AI 編集者への世界観・過去章 Q&A
 */
export async function askBible(input: AskBibleRequest): Promise<AskBibleResponse> {
  const res = await fetch(`${BASE}/ask-bible`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleResponse<AskBibleResponse>(res);
}

/**
 * 執筆テキストと設定情報のリアルタイム矛盾診断
 */
export async function auditConsistency(input: ConsistencyAuditRequest): Promise<ConsistencyAuditResponse> {
  const res = await fetch(`${BASE}/audit-consistency`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleResponse<ConsistencyAuditResponse>(res);
}

/**
 * Next Beats 3バリエーション（王道・サスペンス・心情）並列生成
 */
export async function generateNextBeats(input: NextBeatsRequest): Promise<NextBeatsResponse> {
  const res = await fetch(`${BASE}/next-beats`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleResponse<NextBeatsResponse>(res);
}

/**
 * 矛盾検出された課題の解決・伏線化・例外登録
 */
export async function resolveIssue(
  issueId: string | number,
  action: "Auto-Fix" | "Foreshadowing" | "Ignore",
  apiKey: string = "default-key"
): Promise<{ status: string; message: string }> {
  const res = await fetch(`/api/issues/${issueId}/resolve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
    },
    body: JSON.stringify({ action }),
  });
  return handleResponse<{ status: string; message: string }>(res);
}
