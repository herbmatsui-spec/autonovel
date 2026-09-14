import React, { useState } from 'react';

interface SubmissionChecklistProps {
  platformName?: string;
  publisherUrl?: string;
  onAllChecked?: () => void;
}

export const SubmissionChecklist: React.FC<SubmissionChecklistProps> = ({
  platformName = 'カクヨム / 小説家になろう',
  publisherUrl = 'https://kakuyomu.jp/my/works',
}) => {
  const [checks, setChecks] = useState({
    aiDisclosure: false,
    ratingGuidelines: false,
    typoCheck: false,
    copyrightCheck: false,
  });

  const allChecked = Object.values(checks).every(Boolean);

  const toggleCheck = (key: keyof typeof checks) => {
    setChecks((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-slate-100 shadow-xl max-w-2xl">
      <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <span>📋 投稿前セーフティチェックリスト</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            アカウントBAN防止およびプラットフォーム規約遵守のための最終確認項目
          </p>
        </div>
        <span
          className={`text-xs px-2.5 py-1 rounded-full font-medium ${
            allChecked
              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
              : 'bg-amber-950 text-amber-400 border border-amber-800'
          }`}
        >
          {allChecked ? '✨ 投稿準備完了' : '⚠️ 未確認項目あり'}
        </span>
      </div>

      <div className="space-y-3 mb-6">
        <label className="flex items-start gap-3 p-3 rounded-xl bg-slate-950 border border-slate-800/80 cursor-pointer hover:bg-slate-800/40 transition-colors">
          <input
            type="checkbox"
            checked={checks.aiDisclosure}
            onChange={() => toggleCheck('aiDisclosure')}
            className="mt-0.5 h-4 w-4 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500"
          />
          <div className="text-xs">
            <span className="font-semibold text-white block mb-0.5">
              「AI生成・支援」設定・タグに正しくチェックを入れましたか？
            </span>
            <span className="text-slate-400">
              文化庁ガイドラインおよび各サイトの規約に基づき、AI支援を受けた作品であることを明記またはタグ設定していること。
            </span>
          </div>
        </label>

        <label className="flex items-start gap-3 p-3 rounded-xl bg-slate-950 border border-slate-800/80 cursor-pointer hover:bg-slate-800/40 transition-colors">
          <input
            type="checkbox"
            checked={checks.ratingGuidelines}
            onChange={() => toggleCheck('ratingGuidelines')}
            className="mt-0.5 h-4 w-4 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500"
          />
          <div className="text-xs">
            <span className="font-semibold text-white block mb-0.5">
              過度な性的・暴力的表現が一般向け規定に収まっていますか？
            </span>
            <span className="text-slate-400">
              一般向けレーティングの場合、過激な描写がないこと。R18相当の場合はノクターン等専用サイトへ分離していること。
            </span>
          </div>
        </label>

        <label className="flex items-start gap-3 p-3 rounded-xl bg-slate-950 border border-slate-800/80 cursor-pointer hover:bg-slate-800/40 transition-colors">
          <input
            type="checkbox"
            checked={checks.typoCheck}
            onChange={() => toggleCheck('typoCheck')}
            className="mt-0.5 h-4 w-4 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500"
          />
          <div className="text-xs">
            <span className="font-semibold text-white block mb-0.5">
              誤字脱字・不自然なAI常套句の推敲を行いましたか？
            </span>
            <span className="text-slate-400">
              アンチAIエモーションリフォームや段落パッチPDCAを通し、人間らしい自然な文体に仕上がっていること。
            </span>
          </div>
        </label>

        <label className="flex items-start gap-3 p-3 rounded-xl bg-slate-950 border border-slate-800/80 cursor-pointer hover:bg-slate-800/40 transition-colors">
          <input
            type="checkbox"
            checked={checks.copyrightCheck}
            onChange={() => toggleCheck('copyrightCheck')}
            className="mt-0.5 h-4 w-4 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500"
          />
          <div className="text-xs">
            <span className="font-semibold text-white block mb-0.5">
              他者の著作権・商標権を侵害する固有名詞や盗用を含んでいませんか？
            </span>
            <span className="text-slate-400">
              完全オリジナルまたは権利処理済みの創作物であることを確認済みであること。
            </span>
          </div>
        </label>
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-slate-800">
        <a
          href={publisherUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-xl transition-colors shadow-lg shadow-indigo-600/20"
        >
          <span>🔗 {platformName} 投稿管理画面を開く</span>
          <span className="text-[10px] bg-indigo-950 px-1.5 py-0.5 rounded">外部別タブ</span>
        </a>
        <span className="text-[11px] text-slate-400">
          {allChecked ? 'すべての項目を確認しました。安心してお進みください。' : 'すべての項目にチェックを入れてください'}
        </span>
      </div>
    </div>
  );
};
