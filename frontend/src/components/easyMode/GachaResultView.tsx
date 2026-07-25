import React from "react";
import { GachaResponse } from "../../types/easyMode";
import { GachaCard } from "./GachaCard";

interface GachaResultViewProps {
  response: GachaResponse;
  selectedPlanId: string | null;
  onSelectPlan: (planId: string) => void;
  onGenerateDigest: () => void;
  isLoadingDigest: boolean;
}

export const GachaResultView: React.FC<GachaResultViewProps> = ({
  response,
  selectedPlanId,
  onSelectPlan,
  onGenerateDigest,
  isLoadingDigest,
}) => {
  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="text-center space-y-1">
        <h2 className="text-2xl font-bold text-white">✨ 3つの企画案が届きました！</h2>
        <p className="text-sm text-slate-400">
          気になる企画カードを選択して「ダイジェスト版を生成」を押してください。
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {response.plans.map((plan) => (
          <GachaCard
            key={plan.plan_id}
            plan={plan}
            isSelected={selectedPlanId === plan.plan_id}
            onSelect={onSelectPlan}
          />
        ))}
      </div>

      <div className="flex justify-center pt-4">
        <button
          onClick={onGenerateDigest}
          disabled={!selectedPlanId || isLoadingDigest}
          className="px-8 py-3.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold rounded-xl shadow-lg shadow-emerald-500/20 disabled:opacity-40 transition duration-200 flex items-center gap-2 text-base"
        >
          {isLoadingDigest ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span>プロット・第1話・見せ場を高速生成中...</span>
            </>
          ) : (
            <span>⚡ 選択した案でダイジェスト（試読版）を生成！</span>
          )}
        </button>
      </div>
    </div>
  );
};
