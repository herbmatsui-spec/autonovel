import React from "react";

interface BookCoverPreviewProps {
  title: string;
  author: string;
  content: string; // Used to extract genre or generate catchphrase
}

export const BookCoverPreview: React.FC<BookCoverPreviewProps> = ({
  title,
  author,
  content,
}) => {
  // Extract genre from content or use a default
  const genre = "ファンタジー"; // This could be improved with actual genre detection
  
  // Generate a simple tagline from the content (first sentence or so)
const tagline = content
      ? (content.split(/[。．\n]/)[0] ?? "").slice(0, 50) + "..."
      : "";

  return (
    <div className="book-cover-preview">
      <div className="book-cover">
        {/* Cover background */}
        <div className="book-cover-background">
          {/* Title */}
          <h1 className="book-cover-title">{title}</h1>
          {/* Author */}
          <p className="book-cover-author">{author}</p>
          {/* Genre badge */}
          <span className="book-cover-genre-badge">{genre}</span>
        </div>
        {/* Spine (left side) */}
        <div className="book-cover-spine">
          <div className="book-cover-spine-text">{title}</div>
        </div>
      </div>
      {/* Obi (band) */}
      <div className="book-cover-obi">
        <p className="book-obi-text">{tagline}</p>
      </div>
    </div>
  );
};