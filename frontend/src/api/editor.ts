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
  AuditFastHybridRequest,
  UnifiedAuditReport,
} from "../types/editor";
import { apiFetch, handleResponse as handleApiResponse } from "./client";

const BASE = "/api/editor";

/**
 * インライン AI アシスト（五感描写拡張・Show Don't Tell・トーン書き換え）
 */
export async function assistContent(input: AssistRequest): Promise<AssistResponse> {
  const res = await apiFetch(`${BASE}/assist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleApiResponse<AssistResponse>(res);
}

/**
 * GraphRAG 専属 AI 編集者への世界観・過去章 Q&A
 */
export async function askBible(input: AskBibleRequest): Promise<AskBibleResponse> {
  const res = await apiFetch(`${BASE}/ask-bible`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleApiResponse<AskBibleResponse>(res);
}

/**
 * 執筆テキストと設定情報のリアルタイム矛盾診断
 */
export async function auditConsistency(input: ConsistencyAuditRequest): Promise<ConsistencyAuditResponse> {
  const res = await apiFetch(`${BASE}/audit-consistency`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleApiResponse<ConsistencyAuditResponse>(res);
}

/**
 * Next Beats 3バリエーション（王道・サスペンス・心情）並列生成
 */
export async function generateNextBeats(input: NextBeatsRequest): Promise<NextBeatsResponse> {
  const res = await apiFetch(`${BASE}/next-beats`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleApiResponse<NextBeatsResponse>(res);
}

/**
 * 矛盾検出された課題の解決・伏線化・例外登録
 */
export async function resolveIssue(
  issueId: string | number,
  action: "Auto-Fix" | "Foreshadowing" | "Ignore",
  apiKey: string = "default-key"
): Promise<{ status: string; message: string }> {
  const res = await apiFetch(`/api/issues/${issueId}/resolve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
    },
    body: JSON.stringify({ action }),
  });
  return handleApiResponse<{ status: string; message: string }>(res);
}

/**
 * v5.0: 二層ハイブリッド監査（静的ルール解析＋定性判定）
 */
export async function runHybridAudit(input: AuditFastHybridRequest): Promise<UnifiedAuditReport> {
  const res = await apiFetch(`${BASE}/audit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleApiResponse<UnifiedAuditReport>(res, "二層ハイブリッド監査の実行に失敗しました");
}