import React, { useState } from "react";

interface PromoCardGeneratorProps {
  title: string;
  author: string;
  content: string; // Used to generate tagline and catchcopy
}

export const PromoCardGenerator: React.FC<PromoCardGeneratorProps> = ({
  title,
  author,
  content,
}) => {
  // Extract a catchy tagline from the content (first meaningful sentence)
  const tagline = content
    .split(/[。．\n]/)[0] // Split by Japanese period or newline
    .slice(0, 60) + (content.split(/[。．\n]/)[0].length > 60 ? "..." : "");

  // Generate a compelling catchcopy (marketing copy)
  const catchcopy = `「${title}」――${author}が贈る、心を揺さぶる物語。ページをめくるごとに、新たな発見と感動が待っています。`;

  // Generate hashtags based on content analysis (simplified)
  const hashtags = ["#Web小説", "#小説", "#読書", "#本"];
  
  // State for generated text
  const [generatedText, setGeneratedText] = useState("");
  const [isCopying, setIsCopying] = useState(false);
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  // Generate the Twitter/X post text
  const generatePostText = () => {
    const text = `${title}がついに登場！${tagline} ${hashtags.map(tag => tag).join(" ")}`;
    setGeneratedText(text);
    return text;
  };

  // Copy to clipboard
  const handleCopyToClipboard = async () => {
    if (!generatedText) {
      generatePostText();
    }
    
    try {
      await navigator.clipboard.writeText(generatedText);
      setIsCopying(true);
      setTimeout(() => setIsCopying(false), 2000);
    } catch (err) {
      console.error("Failed to copy text: ", err);
    }
  };

  // Generate and download image as PNG using canvas
  const handleGenerateAndDownloadImage = async () => {
    setIsGeneratingImage(true);
    
    try {
      // Create canvas element
      const canvas = document.createElement('canvas');
      const width = 1200;
      const height = 630; // 16:9 ratio
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      
      if (!ctx) {
        throw new Error('Could not get canvas context');
      }
      
      // Draw gradient background
      const gradient = ctx.createLinearGradient(0, 0, 0, height);
      gradient.addColorStop(0, '#667eea');
      gradient.addColorStop(1, '#764ba2');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);
      
      // Draw title
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 48px "Noto Serif JP", serif';
      ctx.textAlign = 'center';
      ctx.fillText(title, width / 2, height * 0.3);
      
      // Draw tagline
      ctx.font = '24px "Noto Serif JP", serif';
      ctx.fillText(tagline, width / 2, height * 0.45);
      
      // Draw catchcopy (wrapped text)
      ctx.font = '20px "Noto Serif JP", serif';
      ctx.textAlign = 'center';
      const lines = wrapText(ctx, catchcopy, width - 100, 24);
      let startY = height * 0.6;
      lines.forEach((line, index) => {
        ctx.fillText(line, width / 2, startY + index * 28);
      });
      
      // Draw author
      ctx.font = 'italic 24px "Noto Serif JP", serif';
      ctx.fillText(`― ${author} ―`, width / 2, height * 0.85);
      
      // Convert to PNG and trigger download
      canvas.toBlob((blob) => {
        if (blob) {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `${encodeURIComponent(title)}_promo.png`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
        }
        setIsGeneratingImage(false);
      }, 'image/png');
    } catch (err) {
      console.error("Failed to generate image: ", err);
      setIsGeneratingImage(false);
      // Fallback to text file
      handleDownloadTextFallback();
    }
  };

  // Fallback to text file download if canvas fails
  const handleDownloadTextFallback = () => {
    const dummyContent = `Promo Card for "${title}" by ${author}\n\n${tagline}\n\n${catchcopy}\n\nGenerated Text:\n${generatedText}`;
    const blob = new Blob([dummyContent], { type: "text/plain" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title}_promo.txt`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  // Helper function to wrap text to fit within maxWidth
  const wrapText = (ctx: CanvasRenderingContext2D, text: string, maxWidth: number, lineHeight: number): string[] => {
    const words = text.split(' ');
    const lines: string[] = [];
    let currentLine = words[0];

    for (let i = 1; i < words.length; i++) {
      const word = words[i];
      const width = ctx.measureText(currentLine + " " + word).width;
      if (width < maxWidth) {
        currentLine += " " + word;
      } else {
        lines.push(currentLine);
        currentLine = word;
      }
    }
    lines.push(currentLine);
    return lines;
  };

  // Generate initial post text
  React.useEffect(() => {
    generatePostText();
  }, [title, tagline, hashtags]);

  return (
    <div className="promo-card-generator">
      <div className="promo-card-preview">
        {/* Gradient background */}
        <div className="promo-card-background">
          {/* Title */}
          <h1 className="promo-card-title">{title}</h1>
          {/* Tagline (one-line summary) */}
          <p className="promo-card-tagline">{tagline}</p>
          {/* Catchcopy (appealing text) */}
          <p className="promo-card-catchcopy">{catchcopy}</p>
          {/* Author */}
          <p className="promo-card-author">― {author} ―</p>
        </div>
      </div>
      
      {/* Controls */}
      <div className="promo-card-controls">
        <div className="promo-card-actions">
          <button 
            className="promo-card-action-btn"
            onClick={handleCopyToClipboard}
            disabled={isCopying}
          >
            {isCopying ? "✅ コピー済み！" : "📋 投稿文をコピー"}
          </button>
          <button 
            className="promo-card-action-btn"
            onClick={handleGenerateAndDownloadImage}
            disabled={isGeneratingImage}
          >
            {isGeneratingImage ? "🖼️ 生成中..." : "🖼️ 高品質画像をダウンロード"}
          </button>
        </div>
        <div className="promo-card-preview-text">
          <h4>生成された投稿文:</h4>
          <p className="promo-card-generated-text">
            {generatedText}
          </p>
          {!generatedText && <p className="promo-card-placeholder">投稿文を生成中...</p>}
        </div>
      </div>
    </div>
  );
};