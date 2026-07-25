export type GachaPlanType = "royal" | "curveball" | "dark";

export type DigestStatus = "processing" | "completed" | "failed";

export interface GachaPlan {
  plan_id: string;
  plan_type: GachaPlanType;
  title: string;
  logline: string;
  protagonist_summary: string;
  charm_point: string;
}

export interface GachaRequest {
  genre: string;
  keywords: string[];
  temperature: number;
}

export interface GachaResponse {
  request_id: string;
  plans: GachaPlan[];
}

export interface DigestRequest {
  request_id: string;
  selected_plan_id: string;
}

export interface DigestResponse {
  book_id: string;
  title: string;
  synopsis: string;
  episode_1_text: string;
  climax_preview_text: string;
  status: DigestStatus;
}

export interface PromotionRequest {
  book_id: string;
}

export interface PromotionResponse {
  success: boolean;
  redirect_url: string;
  state_token: string;
}
