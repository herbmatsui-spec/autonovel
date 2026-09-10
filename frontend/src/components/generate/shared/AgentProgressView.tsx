import React from "react";
import type { AgentName } from "../types/orchestrated";

interface AgentProgressViewProps {
  agentProgress: Record<AgentName, { status: string; payload?: any }>;
}

export default function AgentProgressView({ agentProgress }: AgentProgressViewProps) {
  return (
    <div className="form-group">
      <label className="label">エージェント進捗状況</label>
      <div>
        {Object.keys(agentProgress).map(agent => (
          <div key={agent} style={{ marginBottom: "4px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>
              {agent === "planning" && "🎯 Planning"} ||
              {agent === "plot" && "📖 Plot"} ||
              {agent === "bible" && "📚 Bible"} ||
              {agent === "context_builder" && "🏗️ ContextBuilder"} ||
              {agent === "writing" && "✍️ Writing"} ||
              {agent === "enrichment" && "🌟 Enrichment"} ||
              {agent === "audit" && "🔍 Audit"} ||
              {agent === "illustration" && "🎨 Illustration"} ||
              {agent === "marketing" && "📢 Marketing"}
            </span>
            <span>
              {agentProgress[agent as AgentName]?.status === "pending" && "⏳ 待機中"} ||
              {agentProgress[agent as AgentName]?.status === "running" && "🔄 実行中"} ||
              {agentProgress[agent as AgentName]?.status === "completed" && "✅ 完了"} ||
              {agentProgress[agent as AgentName]?.status === "failed" && "❌ 失敗"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}