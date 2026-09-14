import React from "react";

interface MultimediaPreviewPanelProps {
  sceneName: string | null;
  imageUrl?: string | undefined;
}

export const MultimediaPreviewPanel: React.FC<MultimediaPreviewPanelProps> = ({
  sceneName,
  imageUrl,
}) => {
  return (
    <div
      className="multimedia-preview-panel"
      style={{
        width: "300px",
        height: "100%",
        borderLeft: "1px solid var(--border-color)",
        backgroundColor: "var(--bg-secondary)",
        display: "flex",
        flexDirection: "column",
        padding: "16px",
        gap: "12px",
        overflowY: "auto",
        boxSizing: "border-box",
      }}
    >
      <h3 style={{ 
        fontSize: "0.9rem", 
        fontWeight: "bold", 
        color: "var(--text-muted)", 
        margin: 0,
        display: "flex",
        alignItems: "center",
        gap: "8px"
      }}>
        🖼️ シーンプレビュー
      </h3>

      <div
        style={{
          flex: 1,
          position: "relative",
          borderRadius: "8px",
          overflow: "hidden",
          backgroundColor: "rgba(0,0,0,0.2)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          border: "1px solid var(--border-color)",
          minHeight: "200px"
        }}
      >
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={sceneName || "Scene Preview"}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              display: "block",
            }}
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).src = "https://via.placeholder.com/300x400?text=Image+Not+Found";
            }}
          />
        ) : (
          <div style={{ 
            textAlign: "center", 
            color: "var(--text-muted)", 
            fontSize: "0.8rem", 
            padding: "20px" 
          }}>
            {sceneName ? (
              <>
                <div style={{ fontSize: "2rem", marginBottom: "8px" }}>🔍</div>
                <div>「{sceneName}」の画像を<br />生成または選択してください</div>
              </>
            ) : (
              <>
                <div style={{ fontSize: "2rem", marginBottom: "8px" }}>📝</div>
                <div>テキスト内の画像マーカー<br />[[img:シーン名]] を検出中...</div>
              </>
            )}
          </div>
        )}
      </div>

      {sceneName && (
        <div
          style={{
            padding: "8px 12px",
            backgroundColor: "rgba(139, 92, 246, 0.1)",
            borderRadius: "4px",
            border: "1px solid rgba(139, 92, 246, 0.2)",
            fontSize: "0.8rem",
            color: "var(--text-primary)"
          }}
        >
          <strong>現在のシーン:</strong> {sceneName}
        </div>
      )}
    </div>
  );
};
