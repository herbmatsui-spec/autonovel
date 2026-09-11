import React from "react";
import { BookItem } from "../../types";
import { BookshelfModal } from "./BookshelfModal";

interface BookSelectorProps {
  currentBook: BookItem | null;
  books: BookItem[];
  onSelectBook: (book: BookItem) => void;
  onCreateBook: (payload: { title: string; genre: string; concept: string; synopsis: string; target_eps: number }) => void;
}

export const BookSelector: React.FC<BookSelectorProps> = ({
  currentBook,
  books,
  onSelectBook,
  onCreateBook,
}) => {
  const [isModalOpen, setIsModalOpen] = React.useState(false);

  return (
    <>
      <button
        className="book-selector"
        onClick={() => setIsModalOpen(true)}
        aria-label="作品選択"
        aria-haspopup="dialog"
      >
        <span className="book-selector__icon">📖</span>
        <span className="book-selector__title">
          {currentBook?.title || "作品を選択"}
        </span>
        <span className="book-selector__chevron">▼</span>
      </button>

      <BookshelfModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        books={books}
        selectedBook={currentBook}
        onSelectBook={(book) => {
          onSelectBook(book);
          setIsModalOpen(false);
        }}
        onCreateBook={onCreateBook}
      />
    </>
  );
};