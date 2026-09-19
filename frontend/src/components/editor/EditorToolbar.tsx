import React, { useState } from "react";
import { EditorFontFamily, EditorFontSize } from "../../types";
import { PlatformCopyButton } from "../common/PlatformCopyButton";
import { SocialReactionModal, StreamComment, ForumPost } from "./SocialReactionModal";

interface EditorToolbarProps {
  fontFamily: EditorFontFamily;
  onFontFamilyChange: (family: EditorFontFamily) => void;
  fontSize: EditorFontSize;
  onFontSizeChange: (size: EditorFontSize) => void;
  onZenModeToggle: () => void;
  isZenMode: boolean;
  manuscriptPages: number;
  onSynthesizeAudio?: () => void;
  isSynthesizingAudio?: boolean;
  chapterTitle: string;
  chapterBody: string;
  onInsertSocialReaction?: (text: string) => void;
}

export const EditorToolbar: React.FC<EditorToolbarProps> = ({
  fontFamily,
  onFontFamilyChange,
  fontSize,
  onFontSizeChange,
  onZenModeToggle,
  isZenMode,
  manuscriptPages,
  onSynthesizeAudio,
  isSynthesizingAudio = false,
  chapterTitle,
  chapterBody,
  onInsertSocialReaction,
}) => {
  const [showSocialModal, setShowSocialModal] = useState(false);

  const handleSocialReactionInsert = (text: string) => {
    if (onInsertSocialReaction) {
      onInsertSocialReaction(text);
    }
    setShowSocialModal(false);
  };

  const handleOpenSocialModal = () => {
    setShowSocialModal(true);
  };

  return (
    <div className="editor-toolbar">
      <div className="editor-toolbar__group">
        <button
          type="button"
          className={`editor-toolbar__btn ${fontFamily === "serif" ? "active" : ""}`}
          onClick={() => onFontFamilyChange("serif")}
          title="明朝体 (しっぽり明朝)"
        >
          明朝
        </button>
        <button
          type="button"
          className={`editor-toolbar__btn ${fontFamily === "sans" ? "active" : ""}`}
          onClick={() => onFontFamilyChange("sans")}
          title="ゴシック体"
        >
          ゴシック
        </button>
      </div>

      <div className="editor-toolbar__divider" />

      <div className="editor-toolbar__group">
        <button
          type="button"
          className="editor-toolbar__btn"
          onClick={() => onFontSizeChange("small")}
          title="小 (15px)"
        >
          A<sub>小</sub>
        </button>
        <button
          type="button"
          className={`editor-toolbar__btn ${fontSize === "medium" ? "active" : ""}`}
          onClick={() => onFontSizeChange("medium")}
          title="中 (17px)"
        >
          A<sub>中</sub>
        </button>
        <button
          type="button"
          className={`editor-toolbar__btn ${fontSize === "large" ? "active" : ""}`}
          onClick={() => onFontSizeChange("large")}
          title="大 (19px)"
        >
          A<sub>大</sub>
        </button>
      </div>

      <div className="editor-toolbar__divider" />

      <div className="editor-toolbar__manuscript" title="原稿用紙換算">
        📄 約{manuscriptPages}枚
      </div>

      <div className="editor-toolbar__divider" />

      <PlatformCopyButton title={chapterTitle} body={chapterBody} />

      <div className="editor-toolbar__divider" />

      {onSynthesizeAudio && (
        <button
          type="button"
          className="editor-toolbar__btn"
          onClick={onSynthesizeAudio}
          disabled={isSynthesizingAudio}
          title="この章の音声を合成する"
        >
          {isSynthesizingAudio ? "⏳ 合成中..." : "🔊 音声朗読"}
        </button>
      )}

      <div className="editor-toolbar__divider" />

      <button
        type="button"
        className="editor-toolbar__btn"
        onClick={handleOpenSocialModal}
        title="配信コメント・掲示板スレッドを生成・挿入"
      >
        💬 配信/掲示板演出
      </button>

      <div className="editor-toolbar__divider" />

      <button
        type="button"
        className={`editor-toolbar__btn editor-toolbar__btn--zen ${isZenMode ? "active" : ""}`}
        onClick={onZenModeToggle}
        title={isZenMode ? "Zenモードを終了 (Esc)" : "Zenモードで集中執筆"}
      >
        {isZenMode ? "⛶ 通常モード" : "🧘 Zen"}
      </button>

      <SocialReactionModal
        isOpen={showSocialModal}
        onClose={() => setShowSocialModal(false)}
        onInsert={handleSocialReactionInsert}
      />
    </div>
  );
};