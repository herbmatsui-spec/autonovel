/**
 * Client API for web novel publishing export and preview (Step 64).
 */

export interface PublishPreviewResponse {
  book_id: number;
  platform: string;
  chapter_number: number;
  title: string;
  formatted_content: string;
  content_body_only: string;
  foreword: string;
  afterword: string;
  warnings: string[];
}

export async function fetchPublishPreview(
  platform: string,
  bookId: number,
  chapterNumber: number = 1,
  branchId?: number
): Promise<PublishPreviewResponse> {
  const params = new URLSearchParams({
    book_id: String(bookId),
    chapter_number: String(chapterNumber),
  });
  if (branchId !== undefined) {
    params.append('branch_id', String(branchId));
  }

  const res = await fetch(`/api/export/publish/${encodeURIComponent(platform)}/preview?${params.toString()}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `プレビュー取得に失敗しました (HTTP ${res.status})`);
  }
  return res.json();
}

export async function downloadPublishZip(
  platform: string,
  bookId: number,
  branchId?: number
): Promise<void> {
  const res = await fetch(`/api/export/publish/${encodeURIComponent(platform)}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      book_id: bookId,
      branch_id: branchId ?? null,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `ZIPエクスポートに失敗しました (HTTP ${res.status})`);
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;

  const disposition = res.headers.get('Content-Disposition');
  let filename = `${platform}_novel_export.zip`;
  if (disposition && disposition.includes("filename*=UTF-8''")) {
    filename = decodeURIComponent(disposition.split("filename*=UTF-8''")[1]);
  } else if (disposition && disposition.includes('filename=')) {
    filename = disposition.split('filename=')[1].replace(/["']/g, '');
  }

  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}
