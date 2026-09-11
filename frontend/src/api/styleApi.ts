import {
  DistillRequest,
  DistillResponse,
  ReformatResponse,
  StylePresetSummary,
  StyleEntry,
  StyleCategory,
} from "../types/style";
import { StyleTuningParams } from "../types/styleComparison";

const BASE = "/api/styles";

export async function fetchStylePresets(): Promise<StylePresetSummary[]> {
  const res = await fetch(`${BASE}/presets`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchAllStyles(): Promise<StyleEntry[]> {
  const res = await fetch(`${BASE}/all`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchStyleCategories(): Promise<StyleCategory[]> {
  const res = await fetch(`${BASE}/categories`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchStylePreview(styleId: string): Promise<StyleEntry> {
  const res = await fetch(`${BASE}/${styleId}/preview`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getStyleComparisonPreview(styleId: string, sceneId: string, params: StyleTuningParams): Promise<string> {
  const query = new URLSearchParams();
  query.append("scene_id", sceneId);
  query.append("kemeritsu", params.kemeritsu.toString());
  query.append("bodyStop", params.bodyStop.toString());
  query.append("metaphor", params.metaphor.toString());
  const res = await fetch(`${BASE}/${styleId}/preview?${query.toString()}`);
  if (!res.ok) throw new Error(await res.text());
  return res.text();
}

export async function distillStyleFromText(request: DistillRequest): Promise<DistillResponse> {
  const res = await fetch(`${BASE}/distill`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function reformatCadence(text: string): Promise<ReformatResponse> {
  const res = await fetch(`${BASE}/reformat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
