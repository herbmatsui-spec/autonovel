import {
  GachaRequest,
  GachaResponse,
  DigestRequest,
  DigestResponse,
  PromotionRequest,
  PromotionResponse,
} from "../types/easyMode";
import { getErrorMessage } from "../lib/utils";

const API_BASE_URL = "/api/easy-mode";

export const fetchGachaPlans = async (
  request: GachaRequest
): Promise<GachaResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/gacha`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request)
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || "ガチャの生成に失敗しました。");
    }
    return data;
  } catch (error: unknown) {
    console.error("fetchGachaPlans error:", error);
    throw new Error(getErrorMessage(error) || "ガチャの生成に失敗しました。");
  }
};

export const fetchDigest = async (
  request: DigestRequest
): Promise<DigestResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/digest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request)
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || "ダイジェストの生成に失敗しました。");
    }
    return data;
  } catch (error: unknown) {
    console.error("fetchDigest error:", error);
    throw new Error(getErrorMessage(error) || "ダイジェストの生成に失敗しました。");
  }
};

export const promoteToAdvanced = async (
  request: PromotionRequest
): Promise<PromotionResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/promote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request)
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || "上級者モードへの引継ぎに失敗しました。");
    }
    return data;
  } catch (error: unknown) {
    console.error("promoteToAdvanced error:", error);
    throw new Error(getErrorMessage(error) || "上級者モードへの引継ぎに失敗しました。");
  }
};
