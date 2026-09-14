import React, { useState, useEffect, useRef } from 'react';
import { useNovelContext } from '../../context/NovelContext';

interface VerticalBookReaderModalProps {
  isOpen: boolean;
  onClose: () => void;
  content: string;
  bookTitle?: string;
}

export const VerticalBookReaderModal: React.FC<VerticalBookReaderModalProps> = ({
  isOpen,
  onClose,
  content,
  bookTitle,
}) => {
  const { character } = useNovelContext();
  const [currentPage, setCurrentPage] = useState(0);
  const [pages, setPages] = useState<string[]>([]);
  const [isAnimating, setIsAnimating] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const pageTurnSoundRef = useRef<HTMLAudioElement>(null);

  // Split content into pages (simple implementation)
  useEffect(() => {
    if (!content) return;

    const wordsPerPage = 400; // Japanese novels typically have ~400 characters per page
    const words = content.split('');
    const newPages: string[] = [];
    
    for (let i = 0; i < words.length; i += wordsPerPage) {
      newPages.push(words.slice(i, i + wordsPerPage).join(''));
    }
    
    setPages(newPages);
    setCurrentPage(0);
  }, [content]);

  // Keyboard controls
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        turnPage('next');
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        turnPage('prev');
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, currentPage, pages]);

  const turnPage = (direction: 'next' | 'prev') => {
    if (isAnimating) return;
    
    setIsAnimating(true);
    
    setCurrentPage(prev => {
      if (direction === 'next') {
        return Math.min(prev + 1, pages.length - 1);
      } else {
        return Math.max(prev - 1, 0);
      }
    });
    
    // Play page turn sound effect (if available)
    if (pageTurnSoundRef.current) {
      try {
        pageTurnSoundRef.current.currentTime = 0;
        const playPromise = pageTurnSoundRef.current.play();
        if (playPromise && typeof playPromise.catch === 'function') {
          playPromise.catch(() => {});
        }
      } catch {
        // ignore audio play errors in test/restricted environments
      }
    }
    
    setTimeout(() => setIsAnimating(false), 300);
  };

  // Handle touch/swipe for mobile
  const touchStartRef = useRef<number>(0);
  const touchEndRef = useRef<number>(0);

  const handleTouchStart = (e: React.TouchEvent) => {
    const touch = e.touches[0];
    if (touch) touchStartRef.current = touch.clientY;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    const touch = e.changedTouches[0];
    if (!touch) return;
    touchEndRef.current = touch.clientY;
    const diff = touchStartRef.current - touchEndRef.current;
    
    if (Math.abs(diff) > 50) { // Minimum swipe distance
      if (diff > 0) {
        // Swipe up - next page
        turnPage('next');
      } else {
        // Swipe down - previous page
        turnPage('prev');
      }
    }
  };

  const getCurrentPageContent = () => {
    if (pages.length === 0) return '';
    return pages[currentPage] || '';
  };

  const getPageNumberText = () => {
    if (pages.length === 0) return '';
    return `${currentPage + 1} / ${pages.length}`;
  };

  const renderRubyContent = (text: string) => {
    // Simple ruby parsing for display
    return text
      .replace(/｜([^《]+)《([^》]+)》/g, '<ruby>$1<rt>$2</rt></ruby>')
      .replace(/\n/g, '<br />');
  };

  if (!isOpen) return null;

  return (
    <div
      className="vertical-book-reader-modal"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.9)',
        backdropFilter: 'blur(8px)',
        zIndex: 3000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px'
      }}
      onClick={onClose}
    >
      <audio
        ref={pageTurnSoundRef}
        src="/sounds/page-turn.mp3"
        preload="auto"
      />

      <div
        ref={containerRef}
        style={{
          width: '100%',
          maxWidth: '900px',
          height: '85vh',
          backgroundColor: '#F7F4EB',
          borderRadius: '12px',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          position: 'relative'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '16px 24px',
            backgroundColor: 'rgba(247, 244, 235, 0.95)',
            borderBottom: '1px solid #d4cdc0'
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: '1.2rem', color: '#2d2d2d' }}>
              📖 {bookTitle || '小説'} - 縦書きプレビュー
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.9rem', color: '#666' }}>
              {character.name}著 {character.genre}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <span style={{ fontSize: '0.9rem', color: '#666' }}>{getPageNumberText()}</span>
            <button
              onClick={onClose}
              style={{
                padding: '8px 16px',
                borderRadius: '6px',
                border: '1px solid #d4cdc0',
                backgroundColor: 'transparent',
                cursor: 'pointer',
                fontSize: '0.9rem',
                transition: 'all 0.2s ease'
              }}
              onMouseOver={(e) => {
                (e.target as HTMLButtonElement).style.backgroundColor = 'rgba(139, 92, 246, 0.1)';
              }}
              onMouseOut={(e) => {
                (e.target as HTMLButtonElement).style.backgroundColor = 'transparent';
              }}
            >
              ✕ 閉じる (Esc)
            </button>
          </div>
        </div>

        {/* Book content area */}
        <div
          style={{
            flex: 1,
            position: 'relative',
            backgroundColor: '#F7F4EB',
            overflow: 'hidden'
          }}
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
        >
          {/* Page navigation hints */}
          {currentPage > 0 && (
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                bottom: 0,
                width: '40%',
                cursor: 'pointer',
                zIndex: 10,
                background: 'linear-gradient(to right, rgba(247, 244, 235, 0.8), transparent)',
                transition: 'all 0.3s ease'
              }}
              onClick={() => turnPage('prev')}
              title="前のページ (↑/←)"
            />
          )}

          {currentPage < pages.length - 1 && (
            <div
              style={{
                position: 'absolute',
                right: 0,
                top: 0,
                bottom: 0,
                width: '40%',
                cursor: 'pointer',
                zIndex: 10,
                background: 'linear-gradient(to left, rgba(247, 244, 235, 0.8), transparent)',
                transition: 'all 0.3s ease'
              }}
              onClick={() => turnPage('next')}
              title="次のページ (↓/→)"
            />
          )}

          {/* Page content */}
          <div
            style={{
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '40px',
              position: 'relative'
            }}
          >
            <div
              style={{
                width: '100%',
                maxWidth: '500px',
                minHeight: '60vh',
                backgroundColor: 'white',
                borderRadius: '8px',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)',
                padding: '40px 30px',
                position: 'relative',
                transform: isAnimating ? 'scale(0.95)' : 'scale(1)',
                transition: 'transform 0.3s ease',
                writingMode: 'vertical-rl',
                textOrientation: 'upright',
                fontFamily: 'Shippori Mincho, Noto Serif JP, serif',
                fontSize: '18px',
                lineHeight: '2.0',
                letterSpacing: '0.08em',
                color: '#2d2d2d'
              }}
            >
              <div
                dangerouslySetInnerHTML={{ __html: renderRubyContent(getCurrentPageContent()) }}
                style={{ whiteSpace: 'pre-wrap' }}
              />

              {/* Page number */}
              <div
                style={{
                  position: 'absolute',
                  bottom: '20px',
                  right: '20px',
                  fontSize: '0.85rem',
                  color: '#999',
                  fontFamily: 'sans-serif',
                  writingMode: 'horizontal-tb'
                }}
              >
                P{currentPage + 1}
              </div>

              {/* Page turn indicators */}
              {currentPage > 0 && (
                <div
                  style={{
                    position: 'absolute',
                    left: '-20px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    backgroundColor: 'rgba(139, 92, 246, 0.2)',
                    border: '2px solid var(--accent-purple)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '20px',
                    opacity: 0.7
                  }}
                >
                  ←
                </div>
              )}

              {currentPage < pages.length - 1 && (
                <div
                  style={{
                    position: 'absolute',
                    right: '-20px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    backgroundColor: 'rgba(139, 92, 246, 0.2)',
                    border: '2px solid var(--accent-purple)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '20px',
                    opacity: 0.7
                  }}
                >
                  →
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '16px 24px',
            backgroundColor: 'rgba(247, 244, 235, 0.95)',
            borderTop: '1px solid #d4cdc0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <div style={{ fontSize: '0.85rem', color: '#666' }}>
            💡 ヒント: ↑/↓矢印キーまたは左右矢印キーでページめくり、Escキーで閉じます
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={() => turnPage('prev')}
              disabled={currentPage === 0}
              style={{
                padding: '8px 16px',
                borderRadius: '6px',
                border: '1px solid #d4cdc0',
                backgroundColor: currentPage === 0 ? 'rgba(0,0,0,0.05)' : 'white',
                cursor: currentPage === 0 ? 'not-allowed' : 'pointer',
                fontSize: '0.85rem',
                opacity: currentPage === 0 ? 0.5 : 1,
                transition: 'all 0.2s ease'
              }}
            >
              ← 前のページ
            </button>

            <button
              onClick={() => turnPage('next')}
              disabled={currentPage === pages.length - 1}
              style={{
                padding: '8px 16px',
                borderRadius: '6px',
                border: '1px solid #d4cdc0',
                backgroundColor: currentPage === pages.length - 1 ? 'rgba(0,0,0,0.05)' : 'white',
                cursor: currentPage === pages.length - 1 ? 'not-allowed' : 'pointer',
                fontSize: '0.85rem',
                opacity: currentPage === pages.length - 1 ? 0.5 : 1,
                transition: 'all 0.2s ease'
              }}
            >
              次のページ →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};