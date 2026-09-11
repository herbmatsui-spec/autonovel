import React, { useState } from "react";
import { VerticalReader } from "./VerticalReader";
import { PromoCardGenerator } from "./PromoCardGenerator";

interface BookShowcaseModalProps {
  onClose: () => void;
  bookData: {
    title: string;
    author: string;
    content: string;
  };
}

export const BookShowcaseModal: React.FC<BookShowcaseModalProps> = ({
  onClose,
  bookData,
}) => {
  const [activeTab, setActiveTab] = useState<"reader" | "promo">("reader");

  return (
    <div className="book-showcase-modal">
      <div className="book-showcase-modal-content">
        <div className="book-showcase-modal-header">
          <h2>📖 成果物ショーケース</h2>
          <button className="book-showcase-modal-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="book-showcase-modal-body">
          <div className="book-showcase-tabs">
            <button
              onClick={() => setActiveTab("reader")}
              className={activeTab === "reader" ? "active" : ""}
            >
              📖 縦書き装丁プレビュー
            </button>
            <button
              onClick={() => setActiveTab("promo")}
              className={activeTab === "promo" ? "active" : ""}
            >
              📢 SNS宣伝カード
            </button>
          </div>
          <div className="book-showcase-tab-content">
            {activeTab === "reader" ? (
              <VerticalReader
                title={bookData.title}
                author={bookData.author}
                content={bookData.content}
              />
            ) : (
              <PromoCardGenerator
                title={bookData.title}
                author={bookData.author}
                content={bookData.content}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};