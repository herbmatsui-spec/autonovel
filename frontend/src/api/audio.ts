import { apiFetch, handleResponse } from "./client";
import {
  AudioTrackInfo,
  AudioSynthesizeRequest,
  AudioSynthesizeResponse,
} from "../types/multimedia";

/**
 * 指定の作品・章に紐づく音声情報を取得する (Step 26)。
 */
export async function fetchChapterAudio(
  bookId: number,
  episodeNum: number
): Promise<AudioTrackInfo | null> {
  try {
    const res = await apiFetch(`/multimedia/audio/${bookId}/${episodeNum}`);
    if (res.status === 404) {
      return null;
    }
    return await handleResponse<AudioTrackInfo>(res, "Failed to fetch chapter audio");
  } catch {
    return null;
  }
}

/**
 * 指定章の音声合成ジョブをトリガーする (Step 26)。
 */
export async function triggerAudioSynthesis(
  payload: AudioSynthesizeRequest
): Promise<AudioSynthesizeResponse> {
  const res = await apiFetch("/multimedia/audio/synthesize", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return await handleResponse<AudioSynthesizeResponse>(res, "Failed to trigger audio synthesis");
}
