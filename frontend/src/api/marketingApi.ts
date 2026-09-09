import { BookShowcaseData, MarketingPromoData } from "../types/marketingShowcase";

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