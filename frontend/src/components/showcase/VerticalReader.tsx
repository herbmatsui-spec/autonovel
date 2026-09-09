import React, { useState, useEffect, useRef } from "react";

interface VerticalReaderProps {
  title: string;
  author: string;
  content: string;
}

export const VerticalReader: React.FC<VerticalReaderProps> = ({
  title,
  author,
  content,
}) => {
  // Process content for vertical writing
  // Convert ruby syntax: |親文字《ルビ》 to <ruby>親文字<rt>ルビ</rt></ruby>
  // Convert Japanese quotation marks and add proper indentation
  
  const processRubyText = (text: string): string => {
    // Replace |親文字《ルビ》 with <ruby>親文字<rt>ルビ</rt></ruby>
    return text.replace(/｜([^《]+)《([^》]+)》/g, '<ruby>$1<rt>$2</rt></ruby>');
  };

  const processIndentationAndQuotes = (text: string): string => {
    // Add full-width space at beginning of paragraphs (blocks separated by double newline)
    // and handle Japanese quotation marks
    return text
      .split("\n\n")
      .map((paragraph) => {
        // Add full-width space (U+3000) at the start of each paragraph
        let processed = "　" + paragraph;
        // Handle Japanese quotation marks if needed
        // For now, we'll keep them as-is since they work in vertical writing
        return processed;
      })
      .join("\n\n");
  };

  const processedContent = processIndentationAndQuotes(
    processRubyText(content)
  );

  // Split into pages (for now, just by double newline)
  const pages = processedContent
    .split("\n\n")
    .map((para) => para.trim())
    .filter((para) => para.length > 0);

  const [currentPage, setCurrentPage] = useState(0);
  const [fontSize, setFontSize] = useState<'small' | 'medium' | 'large'>('medium');
  const [backgroundTheme, setBackgroundTheme] = useState<'washed' | 'white' | 'dark'>('washed');
  const viewportRef = useRef<HTMLDivElement>(null);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === "ArrowRight") {
        setCurrentPage((prev) => Math.min(prev + 1, pages.length - 1));
      } else if (e.key === "ArrowLeft") {
        setCurrentPage((prev) => Math.max(prev - 1, 0));
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [pages.length]);

  // Handle viewport clicks for navigation
  const handleViewportClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!viewportRef.current) return;
    
    const viewportWidth = viewportRef.current.clientWidth;
    const clickX = e.clientX - viewportRef.current.getBoundingClientRect().left;
    
    // If clicked in right half, go to next page; if left half, go to previous page
    if (clickX > viewportWidth / 2) {
      setCurrentPage((prev) => Math.min(prev + 1, pages.length - 1));
    } else {
      setCurrentPage((prev) => Math.max(prev - 1, 0));
    }
  };

  // Font size mapping
  const fontSizeMap = {
    small: '0.8em',
    medium: '1.0em',
    large: '1.2em'
  };

  // Background theme mapping
  const backgroundMap = {
    washed: 'rgba(250, 240, 230, 0.8)', // 生成り和紙
    white: 'rgba(255, 255, 255, 0.9)',   // ホワイト
    dark: 'rgba(20, 20, 30, 0.9)'        // ダーク
  };

  const textColorMap = {
    washed: '#4a4a4a',
    white: '#202020',
    dark: '#f0f0f0'
  };

  return (
    <div className="vertical-reader">
      <div className="vertical-reader-header">
        <h1>{title}</h1>
        <p className="vertical-reader-author">著者: {author}</p>
      </div>
      <div className="vertical-reader-container">
        <div
          className="vertical-book-viewport vertical-reader-viewport"
          ref={viewportRef}
          onClick={handleViewportClick}
          style={{
            fontSize: fontSizeMap[fontSize],
            backgroundColor: backgroundMap[backgroundTheme],
            color: textColorMap[backgroundTheme],
            padding: '20px'
          }}
          dangerouslySetInnerHTML={{ __html: pages.map((page, index) => {
            const isCurrent = index === currentPage;
            return `
              <div class="vertical-reader-page" 
                   data-page-index="${index}"
                   style="${isCurrent ? 'opacity: 1; transform: translateX(0);' : 
                          index < currentPage ? 'opacity: 0.3; transform: translateX(-20px);' : 
                          'opacity: 0.3; transform: translateX(20px);'}"
                   >
                ${page}
              </div>
            `;
          }).join("") }}
        />
      </div>
      <div className="vertical-reader-footer">
        <div className="vertical-reader-customize">
          <div className="customize-group">
            <label htmlFor="font-size-select">文字サイズ:</label>
            <select
              id="font-size-select"
              value={fontSize}
              onChange={(e) => setFontSize(e.target.value as 'small' | 'medium' | 'large')}
              className="customize-select"
            >
              <option value="small">小</option>
              <option value="medium">標準</option>
              <option value="large">大</option>
            </select>
          </div>
          <div className="customize-group">
            <label htmlFor="bg-theme-select">背景色:</label>
            <select
              id="bg-theme-select"
              value={backgroundTheme}
              onChange={(e) => setBackgroundTheme(e.target.value as 'washed' | 'white' | 'dark')}
              className="customize-select"
            >
              <option value="washed">生成り和紙</option>
              <option value="white">ホワイト</option>
              <option value="dark">ダーク</option>
            </select>
          </div>
        </div>
        <div className="vertical-reader-nav">
          <button 
            className="vertical-reader-nav-btn"
            onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 0))}
            disabled={currentPage === 0}
          >
            ＜ 前へ
          </button>
          <span className="vertical-reader-page-info">
            {currentPage + 1} / {pages.length}
          </span>
          <button 
            className="vertical-reader-nav-btn"
            onClick={() => setCurrentPage((prev) => Math.min(prev + 1, pages.length - 1))}
            disabled={currentPage === pages.length - 1}
          >
            次へ ＞
          </button>
        </div>
      </div>
    </div>
  );
};