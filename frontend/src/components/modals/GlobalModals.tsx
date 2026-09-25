import React, { Suspense, lazy } from "react";
import { Modal } from "../common/Modal";
import { Button } from "../common/Button";
import { AssetPackPanel } from "../AssetPackPanel";
import ConfigPanel from "../ConfigPanel";
import { BookshelfModal } from "../common/BookshelfModal";
import { WizardWorkflowPage } from "../../pages/WizardWorkflowPage";
import { useModal } from "../../context/ModalContext";
import { useNovelContext } from "../../context/NovelContext";
import { useNavigate } from "react-router-dom";

const GraphVisualization = lazy(
  () => import("../GraphVisualization")
);

export function GlobalModals() {
  const {
    showGraph,
    setShowGraph,
    showMedia,
    setShowMedia,
    showConfig,
    setShowConfig,
    showBookshelf,
    setShowBookshelf,
    showTransitionOverlay,
    setShowTransitionOverlay,
    showWizardWorkflow,
    setShowWizardWorkflow,
  } = useModal();

  const {
    selectedBookId,
    setSelectedBookId,
    books,
    selectedBook,
    refreshBooks,
  } = useNovelContext();

  const navigate = useNavigate();

  return (
    <>
      {showGraph && (
        <Suspense fallback={null}>
          <GraphVisualization onClose={() => setShowGraph(false)} />
        </Suspense>
      )}

      {/* マルチメディア生成モーダル */}
      <Modal
        isOpen={showMedia}
        onClose={() => setShowMedia(false)}
        title="📦 アセットパック"
        testId="media-modal"
        closeBtnTestId="btn-close-media-modal"
      >
        <AssetPackPanel bookId={selectedBookId} />
      </Modal>

      {/* LLM設定モーダル */}
      <Modal
        isOpen={showConfig}
        onClose={() => setShowConfig(false)}
        title="⚙️ LLM設定"
        testId="config-modal"
        closeBtnTestId="btn-close-config-modal"
        maxWidth={500}
      >
        <ConfigPanel onClose={() => setShowConfig(false)} />
      </Modal>

      {/* Studioモード移行オーバーレイ */}
      <Modal
        isOpen={showTransitionOverlay}
        onClose={() => setShowTransitionOverlay(false)}
        title="🚀 Studioモードへようこそ！"
        testId="transition-overlay"
        closeBtnTestId="btn-close-transition-overlay"
        maxWidth={500}
        zIndex={999}
      >
        <div style={{ textAlign: "left", marginBottom: "24px" }}>
          <p>EasyモードからStudioモードへの移行時に、以下の高度な機能が利用可能になります：</p>
          <ul style={{ paddingLeft: "20px" }}>
            <li>📊 リアルタイム品質スコアと詳細なフィードバック</li>
            <li>🎭 キャラクター詳細プロファイルと関係性マッピング</li>
            <li>🖼️ シーン別マルチメディアプレビューと画像生成</li>
            <li>📖 プロットビジュアライザーとBeatシート編集</li>
            <li>🔍 AI診断による矛盾検出と修正提案</li>
            <li>⚡ ブランチベースの実験的執筆とバージョン管理</li>
          </ul>
        </div>
        <div style={{ display: "flex", justifyContent: "center", gap: "16px" }}>
          <Button variant="primary" onClick={() => {
            setShowTransitionOverlay(false);
            navigate("/studio");
          }}>
            今すぐ体験する
          </Button>
          <Button variant="secondary" onClick={() => {
            setShowTransitionOverlay(false);
            navigate("/");
          }}>
            今はEasyモードで
          </Button>
        </div>
      </Modal>

      {/* 本棚モーダル */}
      <BookshelfModal
        isOpen={showBookshelf}
        onClose={() => setShowBookshelf(false)}
        books={books}
        selectedBook={selectedBook}
        onSelectBook={(book) => {
          setSelectedBookId(book.id);
          setShowBookshelf(false);
        }}
        onCreateBook={async (payload) => {
          const { createBook } = await import("../../api/books");
          const newBook = await createBook(payload);
          await refreshBooks();
          setSelectedBookId(newBook.id);
          setShowBookshelf(false);
        }}
      />

      {/* ウィザードオーバーレイ */}
      {showWizardWorkflow && (
        <div className="wizard-workflow-overlay">
          <div className="flex justify-end mb-4 max-w-4xl mx-auto px-4">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowWizardWorkflow(false)}
              data-testid="close-wizard-btn"
            >
              ✕ ウィザードを閉じる
            </Button>
          </div>
          <WizardWorkflowPage />
        </div>
      )}
    </>
  );
}

export default GlobalModals;
