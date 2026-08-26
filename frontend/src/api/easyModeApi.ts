import {
  GachaRequest,
  GachaResponse,
  DigestRequest,
  DigestResponse,
  PromotionRequest,
  PromotionResponse,
} from "../types/easyMode";
import { request } from "../lib/apiClient";
import { getErrorMessage } from "../lib/utils";

export const fetchGachaPlans = async (
  req: GachaRequest,
  apiKey?: string
): Promise<GachaResponse> => {
  try {
    return await request<GachaResponse>("/easy-mode/gacha", {
      method: "POST",
      body: JSON.stringify(req),
      apiKey,
    });
  } catch (error: unknown) {
    console.error("fetchGachaPlans error:", error);
    throw new Error(getErrorMessage(error) || "ガチャの生成に失敗しました。");
  }
};

export const fetchDigest = async (
  req: DigestRequest,
  apiKey?: string
): Promise<DigestResponse> => {
  try {
    return await request<DigestResponse>("/easy-mode/digest", {
      method: "POST",
      body: JSON.stringify(req),
      apiKey,
    });
  } catch (error: unknown) {
    console.error("fetchDigest error:", error);
    throw new Error(getErrorMessage(error) || "ダイジェストの生成に失敗しました。");
  }
};

export const promoteToAdvanced = async (
  req: PromotionRequest,
  apiKey?: string
): Promise<PromotionResponse> => {
  try {
    return await request<PromotionResponse>("/easy-mode/promote", {
      method: "POST",
      body: JSON.stringify(req),
      apiKey,
    });
  } catch (error: unknown) {
    console.error("promoteToAdvanced error:", error);
    throw new Error(getErrorMessage(error) || "上級者モードへの引継ぎに失敗しました。");
  }
};
