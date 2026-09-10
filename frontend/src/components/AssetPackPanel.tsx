import React, { useState } from "react";
import { useMultimedia } from "../hooks/useMultimedia";
import { useToast } from "../hooks/useToast";
import { EbookFormat, MediaMixFormat } from "../types/multimedia";

interface AssetPackPanelProps {
  bookId: number;
}

export const AssetPackPanel: React.FC<AssetPackPanelProps> = ({ bookId }) => {
  const { addToast } = useToast();
  const { loading, error, assetId, taskId, generate, download, reset } = useMultimedia();
  const [includeIF, setIncludeIF] = useState(true);
  const [includeMediaMix, setIncludeMediaMix] = useState(true);
  const [includeEbook, setIncludeEbook] = useState(true);
  const [ebookFmt, setEbookFmt] = useState<EbookFormat[]>(["epub", "pdf"]);
  const [mediaFmt, setMediaFmt] = useState<MediaMixFormat[]>(["manga"]);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  const onGenerate = async () => {
    reset();
    if (downloadUrl) {
      URL.revokeObjectURL(downloadUrl);
      setDownloadUrl(null);
    }
    const res = await generate({
      book_id: bookId,
      include_if_routes: includeIF,
      include_media_mix: includeMediaMix,
      include_ebook: includeEbook,
      ebook_formats: ebookFmt,
      media_mix_formats: mediaFmt,
    });
    if (res) {
      addToast(`✨ アセットパックを生成しました (asset_id=${res.asset_id})`, "success");
    } else {
      addToast("❌ アセットパックの生成に失敗しました", "error");
    }
  };

  const onDownload = async () => {
    if (assetId == null) return;
    const blob = await download(assetId);
    if (blob) {
      const url = URL.createObjectURL(blob);
      setDownloadUrl(url);
      addToast("✅ ダウンロードの準備ができました", "info");
    } else {
      addToast("❌ ダウンロードに失敗しました", "error");
    }
  };

  const toggleEbookFmt = (fmt: EbookFormat) => {
    setEbookFmt((prev) =>
      prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt],
    );
  };
  const toggleMediaFmt = (fmt: MediaMixFormat) => {
    setMediaFmt((prev) =>
      prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt],
    );
  };

  const ebookFormats: { value: EbookFormat; label: string }[] = [
    { value: "epub", label: "EPUB" },
    { value: "pdf", label: "PDF" },
    { value: "mobi", label: "MOBI" },
  ];

  const mediaFormats: { value: MediaMixFormat; label: string }[] = [
    { value: "manga", label: "マンガ" },
    { value: "audio_drama", label: "オーディオドラマ" },
    { value: "video", label: "動画" },
    { value: "light_novel", label: "ライトノベル" },
    { value: "webtoon", label: "Webtoon" },
  ];

  return (
    <div className="asset-pack-panel">
      <header className="asset-pack-panel__header">
        <h2 className="asset-pack-panel__title">📦 マルチメディア二次創作パッケージ</h2>
        <p className="asset-pack-panel__description">
          IFルート本文、メディアミックス用台本、電子書籍ファイル(EPUB/PDF)を一括生成・ZIP圧縮します。
        </p>
      </header>

      <section className="asset-pack-panel__section">
        <h3 className="asset-pack-panel__section-title">パッケージに含めるコンテンツ</h3>
        <div className="asset-pack-panel__toggles">
          <label className="asset-pack-panel__toggle">
            <input
              type="checkbox"
              checked={includeIF}
              onChange={(e) => setIncludeIF(e.target.checked)}
            />
            <span className="asset-pack-panel__toggle-label">IFルート</span>
          </label>
          <label className="asset-pack-panel__toggle">
            <input
              type="checkbox"
              checked={includeMediaMix}
              onChange={(e) => setIncludeMediaMix(e.target.checked)}
            />
            <span className="asset-pack-panel__toggle-label">メディアミックス展開</span>
          </label>
          <label className="asset-pack-panel__toggle">
            <input
              type="checkbox"
              checked={includeEbook}
              onChange={(e) => setIncludeEbook(e.target.checked)}
            />
            <span className="asset-pack-panel__toggle-label">電子書籍</span>
          </label>
        </div>
      </section>

      {includeEbook && (
        <section className="asset-pack-panel__section">
          <h3 className="asset-pack-panel__section-title">電子書籍フォーマット</h3>
          <div className="asset-pack-panel__chip-group">
            {ebookFormats.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                className={`asset-pack-panel__chip ${ebookFmt.includes(value) ? "active" : ""}`}
                onClick={() => toggleEbookFmt(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </section>
      )}

      {includeMediaMix && (
        <section className="asset-pack-panel__section">
          <h3 className="asset-pack-panel__section-title">メディアミックス展開</h3>
          <div className="asset-pack-panel__chip-group">
            {mediaFormats.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                className={`asset-pack-panel__chip ${mediaFmt.includes(value) ? "active" : ""}`}
                onClick={() => toggleMediaFmt(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </section>
      )}

      <div className="asset-pack-panel__actions">
        <button
          type="button"
          className="btn btn-primary asset-pack-panel__btn-generate"
          onClick={onGenerate}
          disabled={loading || bookId < 1}
        >
          {loading ? (
            <>
              <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
              生成中...
            </>
          ) : (
            "📦 アセットパックを生成"
          )}
        </button>

        {assetId != null && !downloadUrl && (
          <button
            type="button"
            className="btn btn-secondary asset-pack-panel__btn-download"
            onClick={onDownload}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                準備中...
              </>
            ) : (
              "⬇ ZIPパッケージをダウンロード"
            )}
          </button>
        )}

        {downloadUrl && (
          <a
            href={downloadUrl}
            download={`asset_pack_${bookId}.zip`}
            className="btn btn-success asset-pack-panel__btn-download"
          >
            ⬇ ZIPパッケージをダウンロード
          </a>
        )}
      </div>

      {error && <p className="asset-pack-panel__error">Error: {error}</p>}
      {taskId && (
        <p className="asset-pack-panel__task-id">task_id: {taskId}</p>
      )}
    </div>
  );
};

export default AssetPackPanel;