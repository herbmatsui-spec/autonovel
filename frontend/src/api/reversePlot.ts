import {
  GeneratedPlotStructure,
  ReversePlotAnswers,
  ReversePlotGenerateRequest,
} from "../types/reversePlot";
import { LLMConfigOverride } from "../types/easyMode";

const BASE = "/easy_mode";

export async function generateReversePlot(
  answers: ReversePlotAnswers | Partial<ReversePlotAnswers>,
  targetEpisodes = 10,
  genre = "ハイファンタジー (R15)",
  llmConfig?: LLMConfigOverride
): Promise<GeneratedPlotStructure> {
  const payload: ReversePlotGenerateRequest = {
    answers,
    target_episodes: targetEpisodes,
    targetEpisodes,
    genre,
    llm_config: (llmConfig && (llmConfig.api_key || llmConfig.provider)) ? llmConfig : undefined,
  };

  const res = await fetch(`${BASE}/reverse-generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

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

  const data = await res.json();

  // camelCase / snake_case 両対応で整形
  const catharsisPattern = data.catharsisPattern || data.catharsis_pattern;

  return {
    arcs: data.arcs || [],
    episodes: data.episodes || [],
    catharsisPattern,
    catharsis_pattern: catharsisPattern,
  };
}
