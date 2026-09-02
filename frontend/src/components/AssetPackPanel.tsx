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
      addToast(`Asset pack generated (asset_id=${res.asset_id})`, "success");
    } else {
      addToast("Failed to generate asset pack", "error");
    }
  };

  const onDownload = async () => {
    if (assetId == null) return;
    const blob = await download(assetId);
    if (blob) {
      const url = URL.createObjectURL(blob);
      setDownloadUrl(url);
      addToast("Download ready — click the link to save the ZIP", "info");
    } else {
      addToast("Download failed", "error");
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

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
      <h2 style={{ margin: 0 }}>Multimedia Asset Pack</h2>
      <p style={{ color: "#666", margin: 0 }}>
        Generate a unified ZIP of IF routes, media-mix scripts, and ebook files for book #{bookId}.
      </p>

      <fieldset style={{ border: "1px solid #ddd", padding: "8px 12px", borderRadius: 6 }}>
        <legend>Include</legend>
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={includeIF}
            onChange={(e) => setIncludeIF(e.target.checked)}
          />
          IF Routes
        </label>
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={includeMediaMix}
            onChange={(e) => setIncludeMediaMix(e.target.checked)}
          />
          Media Mix (台本生成)
        </label>
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={includeEbook}
            onChange={(e) => setIncludeEbook(e.target.checked)}
          />
          eBook (EPUB / PDF)
        </label>
      </fieldset>

      {includeEbook && (
        <fieldset style={{ border: "1px solid #ddd", padding: "8px 12px", borderRadius: 6 }}>
          <legend>eBook formats</legend>
          {(["epub", "pdf", "mobi"] as EbookFormat[]).map((f) => (
            <label key={f} style={{ marginRight: 12 }}>
              <input
                type="checkbox"
                checked={ebookFmt.includes(f)}
                onChange={() => toggleEbookFmt(f)}
              />
              {f.toUpperCase()}
            </label>
          ))}
        </fieldset>
      )}

      {includeMediaMix && (
        <fieldset style={{ border: "1px solid #ddd", padding: "8px 12px", borderRadius: 6 }}>
          <legend>Media Mix formats</legend>
          {(["manga", "audio_drama", "video", "light_novel", "webtoon"] as MediaMixFormat[]).map(
            (f) => (
              <label key={f} style={{ marginRight: 12 }}>
                <input
                  type="checkbox"
                  checked={mediaFmt.includes(f)}
                  onChange={() => toggleMediaFmt(f)}
                />
                {f}
              </label>
            ),
          )}
        </fieldset>
      )}

      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <button onClick={onGenerate} disabled={loading || bookId < 1}>
          {loading ? "Generating..." : "Generate Asset Pack"}
        </button>
        <button onClick={onDownload} disabled={assetId == null}>
          Prepare download
        </button>
        {downloadUrl && (
          <a href={downloadUrl} download={`asset_pack_${bookId}.zip`}>
            ⬇ Download ZIP
          </a>
        )}
      </div>

      {error && <p style={{ color: "crimson" }}>Error: {error}</p>}
      {taskId && (
        <p style={{ color: "#444", fontFamily: "monospace" }}>task_id: {taskId}</p>
      )}
    </div>
  );
};

export default AssetPackPanel;
