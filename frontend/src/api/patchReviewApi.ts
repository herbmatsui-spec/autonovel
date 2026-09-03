const BASE = "/api/patches";

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

// Types (inline for now - can be moved to types/editor.ts later)
export interface ConflictItem {
  category: string;
  severity: "critical" | "high" | "medium" | "low";
  title: string;
  description: string;
  field_path: string | null;
  current_value: string | null;
  suggested_value: string | null;
  evidence_past: string;
  evidence_current: string;
  constraint_for_next: string;
  confidence: number;
}

export interface ConflictReport {
  book_id: number;
  ep_num: number;
  patch_review_id: number | null;
  summary: string;
  total_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  conflicts: ConflictItem[];
}

export interface PatchReview {
  id: number;
  book_id: number;
  ep_num: number;
  patch_type: string;
  original_content: string;
  proposed_content: string;
  diff_json: Record<string, any>;
  status: "generated" | "under_review" | "approved" | "rejected" | "needs_revision" | "expired";
  reviewer_id: string | null;
  reviewed_at: string | null;
  review_comment: string;
  audit_issue_ids: number[];
  learning_metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface SettingVersion {
  id: number;
  book_id: number;
  version_number: number;
  snapshot_json: Record<string, any>;
  base_version_id: number | null;
  change_summary: string;
  created_by: string | null;
  created_at: string;
}

export interface ReviewActionRequest {
  reviewer_id?: string;
  comment: string;
}

export interface ReviseReviewRequest {
  proposed_content: string;
  reviewer_id?: string;
  comment: string;
}

// Patch Review API
export const patchReviewApi = {
  // Get pending reviews for a book
  getPendingReviews: async (bookId: number): Promise<PatchReview[]> => {
    const res = await fetch(`${BASE}/${bookId}/reviews`);
    return handleResponse<PatchReview[]>(res);
  },

  // Get review detail
  getReviewDetail: async (reviewId: number): Promise<PatchReview> => {
    const res = await fetch(`${BASE}/reviews/${reviewId}`);
    return handleResponse<PatchReview>(res);
  },

  // Approve review
  approveReview: async (reviewId: number, data: ReviewActionRequest): Promise<{ message: string }> => {
    const res = await fetch(`${BASE}/reviews/${reviewId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return handleResponse<{ message: string }>(res);
  },

  // Reject review
  rejectReview: async (reviewId: number, data: ReviewActionRequest): Promise<{ message: string }> => {
    const res = await fetch(`${BASE}/reviews/${reviewId}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return handleResponse<{ message: string }>(res);
  },

  // Revise review (submit revised proposal)
  reviseReview: async (reviewId: number, data: ReviseReviewRequest): Promise<{ message: string }> => {
    const res = await fetch(`${BASE}/reviews/${reviewId}/revise`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return handleResponse<{ message: string }>(res);
  },
};

// Setting Version API
export const settingVersionApi = {
  // Get all setting versions for a book
  getSettingVersions: async (bookId: number): Promise<SettingVersion[]> => {
    const res = await fetch(`${BASE}/${bookId}/setting-versions`);
    return handleResponse<SettingVersion[]>(res);
  },

  // Get specific setting version
  getSettingVersion: async (bookId: number, versionNumber: number): Promise<SettingVersion> => {
    const res = await fetch(`${BASE}/${bookId}/setting-versions/${versionNumber}`);
    return handleResponse<SettingVersion>(res);
  },
};