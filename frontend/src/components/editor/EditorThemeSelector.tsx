import React, { useState, useEffect } from "react";
import { EditorThemeConfig } from "../../types/editorLayout";

interface EditorThemeSelectorProps {
  onThemeChange?: (theme: EditorThemeConfig) => void;
  initialConfig?: Partial<EditorThemeConfig>;
}

export const EditorThemeSelector: React.FC<EditorThemeSelectorProps> = ({
  onThemeChange,
  initialConfig,
}) => {
  const [config, setConfig] = useState<EditorThemeConfig>(() => {
    if (typeof window === "undefined") {
      return {
        theme: "dark",
        fontFamily: "serif",
        fontSize: "medium",
        lineHeight: "normal",
        showManuscriptGrid: false,
      };
    }

    try {
      const saved = localStorage.getItem("autonovel.editorThemeConfig");
      if (saved) {
        const parsed = JSON.parse(saved) as EditorThemeConfig;
        return { ...parsed, ...initialConfig };
      }
    } catch (e) {
      console.error("Failed to load theme config from localStorage", e);
    }

    return {
      theme: "dark",
      fontFamily: "serif",
      fontSize: "medium",
      lineHeight: "normal",
      showManuscriptGrid: false,
      ...initialConfig,
    };
  });

  useEffect(() => {
    try {
      localStorage.setItem("autonovel.editorThemeConfig", JSON.stringify(config));
    } catch (e) {
      console.error("Failed to save theme config to localStorage", e);
    }

    onThemeChange?.(config);
  }, [config, onThemeChange]);

  const handleThemeChange = (theme: EditorThemeConfig['theme']) => {
    setConfig(prev => ({ ...prev, theme }));
  };

  const handleFontFamilyChange = (fontFamily: EditorThemeConfig['fontFamily']) => {
    setConfig(prev => ({ ...prev, fontFamily }));
  };

  const handleFontSizeChange = (fontSize: EditorThemeConfig['fontSize']) => {
    setConfig(prev => ({ ...prev, fontSize }));
  };

  const handleLineHeightChange = (lineHeight: EditorThemeConfig['lineHeight']) => {
    setConfig(prev => ({ ...prev, lineHeight }));
  };

  const handleManuscriptGridToggle = () => {
    setConfig(prev => ({ ...prev, showManuscriptGrid: !prev.showManuscriptGrid }));
  };

  const getThemePreviewStyle = () => {
    switch (config.theme) {
      case "paper":
        return {
          backgroundColor: "#F7F4EB",
          color: "#2d2d2d",
          borderColor: "#d4cdc0"
        };
      case "sepia":
        return {
          backgroundColor: "#F4E8D0",
          color: "#3a3a3a",
          borderColor: "#e6d5b8"
        };
      case "cyberpunk":
        return {
          backgroundColor: "#0a0e17",
          color: "#00ff88",
          borderColor: "#00ff88"
        };
      case "dark":
      default:
        return {
          backgroundColor: "#0a0e17",
          color: "#ffffff",
          borderColor: "#333"
        };
    }
  };

  return (
    <div style={{ 
      padding: "24px", 
      backgroundColor: "var(--bg-card)",
      border: "1px solid var(--border-color)",
      borderRadius: "var(--radius-lg)",
      boxShadow: "0 4px 20px rgba(0, 0, 0, 0.3)",
      maxWidth: "400px",
      margin: "0 auto"
    }}>
      <h3 style={{ 
        fontSize: "1.25rem", 
        fontWeight: "700", 
        marginBottom: "20px",
        color: "var(--accent-purple)"
      }}>
        🎨 エディタテーマ設定
      </h3>

      <div style={{ marginBottom: "20px" }}>
        <label style={{ 
          display: "block", 
          fontSize: "0.9rem", 
          fontWeight: "600",
          color: "var(--text-muted)",
          marginBottom: "8px"
        }}>
          テーマ
        </label>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {([
            { key: "dark", label: "🖤 ダーク", previewStyle: { backgroundColor: "#0a0e17", color: "#ffffff", borderColor: "#333" } },
            { key: "paper", label: "📄 ペーパー", previewStyle: { backgroundColor: "#F7F4EB", color: "#2d2d2d", borderColor: "#d4cdc0" } },
            { key: "sepia", label: "☕ セピア", previewStyle: { backgroundColor: "#F4E8D0", color: "#3a3a3a", borderColor: "#e6d5b8" } },
            { key: "cyberpunk", label: "🤖 サイバーパンク", previewStyle: { backgroundColor: "#0a0e17", color: "#00ff88", borderColor: "#00ff88" } }
          ] as const).map(themeOption => (
            <button
              key={themeOption.key}
              type="button"
              className={`btn-tab ${config.theme === themeOption.key ? "btn-tab--active" : ""}`}
              onClick={() => handleThemeChange(themeOption.key)}
              style={{ 
                padding: "8px 12px",
                border: config.theme === themeOption.key ? "2px solid var(--accent-purple)" : "1px solid var(--border-color)",
                backgroundColor: themeOption.previewStyle.backgroundColor,
                color: themeOption.previewStyle.color,
                borderRadius: "8px",
                cursor: "pointer",
                fontSize: "0.85rem",
                fontWeight: 500,
                transition: "all 0.2s ease",
                opacity: config.theme === themeOption.key ? 1 : 0.7,
                transform: config.theme === themeOption.key ? "scale(1.05)" : "scale(1)"
              }}
            >
              {themeOption.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: "20px" }}>
        <label style={{ 
          display: "block", 
          fontSize: "0.9rem", 
          fontWeight: "600",
          color: "var(--text-muted)",
          marginBottom: "8px"
        }}>
          フォントファミリー
        </label>
        <div style={{ display: "flex", gap: "8px" }}>
          {([
            { key: "serif", label: "明朝体", className: "font-serif" },
            { key: "sans", label: "ゴシック体", className: "font-sans" },
            { key: "mincho", label: "Shippori Mincho", className: "font-mincho" }
          ] as const).map(fontOption => (
            <button
              key={fontOption.key}
              type="button"
              onClick={() => handleFontFamilyChange(fontOption.key)}
              className={`btn-tab ${config.fontFamily === fontOption.key ? "btn-tab--active" : ""}`}
              style={{ padding: "6px 12px", fontSize: "0.85rem" }}
            >
              {fontOption.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: "20px" }}>
        <label style={{ 
          display: "block", 
          fontSize: "0.9rem", 
          fontWeight: "600",
          color: "var(--text-muted)",
          marginBottom: "8px"
        }}>
          フォントサイズ
        </label>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {([
            { key: "small", label: "小" },
            { key: "medium", label: "中" },
            { key: "large", label: "大" },
            { key: "huge", label: "特大" }
          ] as const).map(sizeOption => (
            <button
              key={sizeOption.key}
              type="button"
              onClick={() => handleFontSizeChange(sizeOption.key)}
              className={`btn-tab ${config.fontSize === sizeOption.key ? "btn-tab--active" : ""}`}
              style={{ padding: "6px 12px", fontSize: "0.85rem" }}
            >
              {sizeOption.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: "20px" }}>
        <label style={{ 
          display: "block", 
          fontSize: "0.9rem", 
          fontWeight: "600",
          color: "var(--text-muted)",
          marginBottom: "8px"
        }}>
          行間
        </label>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {([
            { key: "tight", label: "狭く" },
            { key: "normal", label: "標準" },
            { key: "relaxed", label: "広く" }
          ] as const).map(lineOption => (
            <button
              key={lineOption.key}
              type="button"
              onClick={() => handleLineHeightChange(lineOption.key)}
              className={`btn-tab ${config.lineHeight === lineOption.key ? "btn-tab--active" : ""}`}
              style={{ padding: "6px 12px", fontSize: "0.85rem" }}
            >
              {lineOption.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: "20px" }}>
        <label style={{ 
          display: "flex",
          alignItems: "center",
          gap: "8px",
          cursor: "pointer"
        }}>
          <input
            type="checkbox"
            checked={config.showManuscriptGrid}
            onChange={handleManuscriptGridToggle}
            style={{ 
              width: "18px",
              height: "18px",
              accentColor: "var(--accent-purple)"
            }}
          />
          <span style={{ 
            fontSize: "0.9rem",
            color: "var(--text-main)",
            fontWeight: 500
          }}>
            原稿用紙風のマス目を表示
          </span>
        </label>
      </div>

      <div style={{ 
        padding: "12px", 
        backgroundColor: "rgba(139, 92, 246, 0.1)",
        border: "1px solid rgba(139, 92, 246, 0.3)",
        borderRadius: "8px",
        fontSize: "0.85rem",
        color: "var(--text-muted)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
          <span>📋 現在の設定:</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", gap: "8px", fontSize: "0.8rem" }}>
          <span>テーマ:</span>
          <span>{config.theme}</span>
          <span>フォント:</span>
          <span>{config.fontFamily}</span>
          <span>サイズ:</span>
          <span>{config.fontSize}</span>
          <span>行間:</span>
          <span>{config.lineHeight}</span>
          <span>マス目:</span>
          <span>{config.showManuscriptGrid ? "ON" : "OFF"}</span>
        </div>
      </div>
    </div>
  );
};