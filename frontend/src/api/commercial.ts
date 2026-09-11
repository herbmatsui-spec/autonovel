/**
 * frontend/src/api/commercial.ts - 商用投稿スケジュール API クライアント
 */

import { apiFetch, handleResponse } from "./client";
import {
  PublicationScheduleCreate,
  PublicationScheduleResponse,
  PublicationScheduleRunNowResponse,
  PublicationScheduleCancelResponse,
} from "../types/commercial";

const BASE_URL = "/api/commercial"; // 実際のエンドポイントパスに合わせて調整

/**
 * 投稿スケジュールを新規登録する
 */
export async function createPublicationSchedule(
  data: PublicationScheduleCreate
): Promise<PublicationScheduleResponse> {
  const res = await apiFetch(`${BASE_URL}/schedules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<PublicationScheduleResponse>(res, "Failed to create publication schedule");
}

/**
 * 書籍ごとの投稿スケジュール一覧を取得する
 */
export async function getPublicationSchedules(
  bookId: number
): Promise<PublicationScheduleResponse[]> {
  const res = await apiFetch(`${BASE_URL}/schedules/${bookId}`, {
    method: "GET",
  });
  return handleResponse<PublicationScheduleResponse[]>(res, "Failed to fetch publication schedules");
}

/**
 * 投稿スケジュールを取り消す
 */
export async function cancelPublicationSchedule(
  scheduleId: number
): Promise<PublicationScheduleCancelResponse> {
  const res = await apiFetch(`${BASE_URL}/schedules/${scheduleId}`, {
    method: "DELETE",
  });
  return handleResponse<PublicationScheduleCancelResponse>(res, "Failed to cancel publication schedule");
}

/**
 * 予約投稿を即時に実行する
 */
export async function runPublicationScheduleNow(
  scheduleId: number
): Promise<PublicationScheduleRunNowResponse> {
  const res = await apiFetch(`${BASE_URL}/schedules/${scheduleId}/run-now`, {
    method: "POST",
  });
  return handleResponse<PublicationScheduleRunNowResponse>(res, "Failed to trigger immediate publication");
}
