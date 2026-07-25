import React from "react";
import { GachaPlan } from "../../types/easyMode";

interface GachaCardProps {
  plan: GachaPlan;
  isSelected: boolean;
  onSelect: (planId: string) => void;
}

const TYPE_CONFIG = {
  royal: { label: "王道案", color: "from-amber-500 to-rose-500", badge: "👑" },
  curveball: { label: "変化球案", color: "from-teal-500 to-emerald-500", badge: "⚡" },
  dark: { label: "ダーク案", color: "from-indigo-500 to-purple-600", badge: "🌙" },
};

export const GachaCard: React.FC<GachaCardProps> = ({
  plan,
  isSelected,
  onSelect,
}) => {
  const config = TYPE_CONFIG[plan.plan_type] || TYPE_CONFIG.royal;

  return (
    <div
      onClick={() => onSelect(plan.plan_id)}
      className={`cursor-pointer rounded-xl border-2 p-5 transition-all duration-200 flex flex-col justify-between ${
        isSelected
          ? "bg-slate-800 border-purple-500 shadow-xl shadow-purple-500/20 scale-[1.02]"
          : "bg-slate-900/90 border-slate-800 hover:border-slate-600 hover:bg-slate-800/60"
      }`}
    >
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span
            className={`text-xs font-bold px-2.5 py-1 rounded-full text-white bg-gradient-to-r ${config.color}`}
          >
            {config.badge} {config.label}
          </span>
          {isSelected && (
            <span className="text-purple-400 font-bold text-xs bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/30">
              選択中
            </span>
          )}
        </div>

        <h3 className="text-lg font-bold text-white leading-snug">
          {plan.title}
        </h3>

        <p className="text-xs text-slate-300 line-clamp-3 bg-slate-950/40 p-2.5 rounded border border-slate-800">
          {plan.logline}
        </p>

        <div className="space-y-1.5 text-xs text-slate-400">
          <div>
            <span className="font-semibold text-slate-300">【主人公】</span>
            {plan.protagonist_summary}
          </div>
          <div>
            <span className="font-semibold text-purple-300">【魅力】</span>
            {plan.charm_point}
          </div>
        </div>
      </div>
    </div>
  );
};
