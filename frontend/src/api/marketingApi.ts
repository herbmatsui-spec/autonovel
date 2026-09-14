import { BookShowcaseData, MarketingPromoData } from "../types/marketingShowcase";
import { ViralTitleRequest, ViralTitleResponse } from "../types/marketing";

const BASE = "/api/marketing";

export async function generateMarketingContent(
  novelTitle: string,
  novelContent: string,
  authorName: string
): Promise<{ showcase: BookShowcaseData; promo: MarketingPromoData }> {
  const res = await fetch(`${BASE}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: novelTitle,
      content: novelContent,
      author: authorName,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function generateViralTitles(
  payload: ViralTitleRequest
): Promise<ViralTitleResponse> {
  const res = await fetch(`${BASE}/viral-titles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || `Request failed with status ${res.status}`);
  }
  return res.json();
}