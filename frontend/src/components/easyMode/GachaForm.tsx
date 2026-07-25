import React, { useState } from "react";
import { GachaRequest } from "../../types/easyMode";

interface GachaFormProps {
  onSubmit: (request: GachaRequest) => void;
  isLoading: boolean;
}

const GENRES = [
  "ハイファンタジー",
  "ローファンタジー",
  "恋愛・ラブコメ",
  "SF・近未来",
  "現代ドラマ・サスペンス",
];

export const GachaForm: React.FC<GachaFormProps> = ({ onSubmit, isLoading }) => {
  const [genre, setGenre] = useState(GENRES[0]);
  const [keywordInput, setKeywordInput] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const keywords = keywordInput
      .split(/[,、\s]+/)
      .map((k) => k.trim())
      .filter((k) => k.length > 0);

    if (keywords.length === 0) {
      setErrorMsg("ジャンルと少なくとも1つのキーワードを入力してください");
      return;
    }

    setErrorMsg("");
    onSubmit({
      genre,
      keywords,
      temperature: 0.7,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="bg-slate-800/80 border border-slate-700 rounded-xl p-6 shadow-xl max-w-xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
          <span>🎰</span> 3案ガチャで小説の企画を作成
        </h2>
        <p className="text-sm text-slate-400">
          ジャンルとキーワードを入力すると、AIが「王道」「変化球」「ダーク」の3つの企画案を即座に生成します。
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            ジャンル
          </label>
          <select
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-purple-500 focus:outline-none"
          >
            {GENRES.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            キーワード（カンマ区切り）
          </label>
          <input
            type="text"
            placeholder="例: 無双, 追放, 魔法学園"
            value={keywordInput}
            onChange={(e) => setKeywordInput(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-purple-500 focus:outline-none"
          />
        </div>

        {errorMsg && (
          <p className="text-sm text-rose-400 font-medium">{errorMsg}</p>
        )}
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold rounded-lg shadow-lg disabled:opacity-50 transition duration-200 flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            <span>AIが3つの企画を考え中...</span>
          </>
        ) : (
          <span>🚀 3案ガチャを引く！</span>
        )}
      </button>
    </form>
  );
};
