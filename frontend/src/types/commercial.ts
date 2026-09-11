/**
 * Commercial Publishing Types
 */

export type CommercialPlatform = 'narou' | 'kakuyomu' | 'kindle' | 'kobo';

export type PublicationScheduleStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface PublicationScheduleCreate {
  book_id: number;
  platform: CommercialPlatform;
  episode_range: [number, number];
  scheduled_at: string; // ISO 8601 string
  credentials_override?: Record<string, any>;
}

export interface PublicationScheduleResponse {
  id: number;
  book_id: number;
  platform: CommercialPlatform;
  episode_range: [number, number];
  scheduled_at: string; // ISO 8601 string
  status: PublicationScheduleStatus;
  error_message?: string | null;
  created_at: string; // ISO 8601 string
}

export interface PublicationScheduleRunNowResponse {
  success: boolean;
  message: string;
  schedule_id: number;
}

export interface PublicationScheduleCancelResponse {
  success: boolean;
  message: string;
  schedule_id: number;
}
