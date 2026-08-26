import React, { useState } from "react";
import {
  GachaRequest,
  GachaResponse,
  DigestResponse,
} from "../../types/easyMode";
import {
  fetchGachaPlans,
  fetchDigest,
  promoteToAdvanced,
} from "../../api/easyModeApi";
import { getErrorMessage, isSafeRedirect } from "../../lib/utils";
import { GachaForm } from "./GachaForm";
import { GachaResultView } from "./GachaResultView";
import { DigestView } from "./DigestView";

type ViewState = "form" | "gacha_result" | "digest_result";

export const EasyModeContainer: React.FC = () => {
  const [viewState, setViewState] = useState<ViewState>("form");
  const [isLoadingGacha, setIsLoadingGacha] = useState(false);
  const [isLoadingDigest, setIsLoadingDigest] = useState(false);
  const [isPromoting, setIsPromoting] = useState(false);

  const [gachaResponse, setGachaResponse] = useState<GachaResponse | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [digestResponse, setDigestResponse] = useState<DigestResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // 1. ガチャ実行
  const handleGachaSubmit = async (request: GachaRequest) => {
    setIsLoadingGacha(true);
    setErrorMessage(null);
    try {
      const res = await fetchGachaPlans(request);
      setGachaResponse(res);
      setViewState("gacha_result");
    } catch (err: unknown) {
      setErrorMessage(getErrorMessage(err) || "ガチャの実行中にエラーが発生しました");
    } finally {
      setIsLoadingGacha(false);
    }
  };

  // 2. ダイジェスト生成
  const handleGenerateDigest = async () => {
    if (!gachaResponse || !selectedPlanId) return;

    setIsLoadingDigest(true);
    setErrorMessage(null);
    try {
      const res = await fetchDigest({
        request_id: gachaResponse.request_id,
        selected_plan_id: selectedPlanId,
      });
      setDigestResponse(res);
      setViewState("digest_result");
    } catch (err: unknown) {
      setErrorMessage(getErrorMessage(err) || "ダイジェスト生成中にエラーが発生しました");
    } finally {
      setIsLoadingDigest(false);
    }
  };

  // 3. 全話生成（通知メッセージ）
  const handleFullGenerate = () => {
    alert(`作品「${digestResponse?.title}」の残り全話の自動執筆を開始します（バックエンドタスク投入）。`);
  };

  // 4. プロデューサー昇格
  const handlePromote = async () => {
    if (!digestResponse) return;

    setIsPromoting(true);
    setErrorMessage(null);
    try {
      const res = await promoteToAdvanced({ book_id: digestResponse.book_id });
      if (res.success) {
        if (isSafeRedirect(res.redirect_url)) {
          window.location.href = res.redirect_url;
        } else {
          setErrorMessage('無効なリダイレクトURLです。');
        }
      }
    } catch (err: unknown) {
      setErrorMessage(getErrorMessage(err) || "昇格処理中にエラーが発生しました");
    } finally {
      setIsPromoting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-8">
      {/* エラーメッセージ表示 */}
      {errorMessage && (
        <div className="max-w-xl mx-auto bg-rose-500/10 border border-rose-500/40 text-rose-300 p-4 rounded-xl text-sm flex items-center justify-between">
          <span>⚠️ {errorMessage}</span>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-xs underline text-rose-400 hover:text-rose-200"
          >
            閉じる
          </button>
        </div>
      )}

      {/* ステップ切り替え表示 */}
      {viewState === "form" && (
        <GachaForm
          onSubmit={handleGachaSubmit}
          isLoading={isLoadingGacha}
        />
      )}

      {viewState === "gacha_result" && gachaResponse && (
        <GachaResultView
          response={gachaResponse}
          selectedPlanId={selectedPlanId}
          onSelectPlan={setSelectedPlanId}
          onGenerateDigest={handleGenerateDigest}
          isLoadingDigest={isLoadingDigest}
        />
      )}

      {viewState === "digest_result" && digestResponse && (
        <DigestView
          digest={digestResponse}
          onFullGenerate={handleFullGenerate}
          onPromote={handlePromote}
          isPromoting={isPromoting}
        />
      )}
    </div>
  );
};
