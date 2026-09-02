export type MediaMixFormat =
  | "manga"
  | "audio_drama"
  | "video"
  | "light_novel"
  | "webtoon";

export type EbookFormat = "epub" | "pdf" | "mobi" | "json";

export interface MediaMixRequest {
  book_id: number;
  format?: MediaMixFormat;
  episode_num?: number;
  include_metadata?: boolean;
}

export interface MediaMixResponse {
  asset_id: number;
  files: string[];
  metadata: Record<string, unknown>;
}

export interface EbookExportRequest {
  book_id: number;
  formats?: EbookFormat[];
  author?: string;
  publisher?: string;
}

export interface EbookExportResponse {
  asset_id: number;
  files: string[];
  formats: string[];
}

export interface IFRouteGenerateRequest {
  book_id: number;
  persist?: boolean;
}

export interface IFRouteResponse {
  asset_id: number;
  nodes: number;
  entry_node_id: string;
  graph: Record<string, unknown>;
}

export interface AssetPackRequest {
  book_id: number;
  include_if_routes?: boolean;
  include_media_mix?: boolean;
  include_ebook?: boolean;
  ebook_formats?: EbookFormat[];
  media_mix_formats?: MediaMixFormat[];
}

export interface AssetPackResponse {
  asset_id: number;
  task_id: string;
  file_count: number;
  file_path: string | null;
}

export interface ArtifactMetaResponse {
  asset_id: number;
  book_id: number;
  asset_type: string;
  format: string;
  file_path: string;
  metadata: Record<string, unknown>;
  created_at: string | null;
}

export interface TaskStatusResponse {
  task_id: string;
  asset_id: number | null;
  status: "pending" | "running" | "completed" | "failed";
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}
