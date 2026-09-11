import React, { useEffect, useRef } from "react";
import { BookItem } from "../../types";

interface BookshelfModalProps {
  isOpen: boolean;
  onClose: () => void;
  books: BookItem[];
  selectedBook: BookItem | null;
  onSelectBook: (book: BookItem) => void;
  onCreateBook: (payload: { title: string; genre: string; concept: string; synopsis: string; target_eps: number }) => void;
}

export const BookshelfModal: React.FC<BookshelfModalProps> = ({
  isOpen,
  onClose,
  books,
  selectedBook,
  onSelectBook,
  onCreateBook,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.addEventListener("keydown", handleEsc);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleEsc);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="bookshelf-modal-overlay"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
      aria-labelledby="bookshelf-title"
    >
      <div className="bookshelf-modal" ref={modalRef}>
        <header className="bookshelf-modal__header">
          <h2 id="bookshelf-title" className="bookshelf-modal__title">📚 本棚</h2>
          <button
            className="bookshelf-modal__close"
            onClick={onClose}
            aria-label="閉じる"
          >
            ✕
          </button>
        </header>
        <div className="bookshelf-modal__body">
          <div className="bookshelf-modal__grid">
            {books.map((book) => (
              <button
                key={book.id}
                className={`bookshelf-modal__card ${book.id === selectedBook?.id ? "selected" : ""}`}
                onClick={() => onSelectBook(book)}
              >
                <div className="bookshelf-modal__card-title">{book.title}</div>
                <div className="bookshelf-modal__card-meta">
                  <span className="badge badge-genre">{book.genre}</span>
                  <span>目標: {book.target_eps}話</span>
                </div>
                <div className="bookshelf-modal__card-date">
                  {new Date(book.created_at).toLocaleDateString("ja-JP")}
                </div>
              </button>
            ))}
            <div className="bookshelf-modal__card bookshelf-modal__card--add">
              <CreateBookForm onCreate={onCreateBook} onClose={onClose} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

interface CreateBookFormProps {
  onCreate: (payload: { title: string; genre: string; concept: string; synopsis: string; target_eps: number }) => void;
  onClose: () => void;
}

const CreateBookForm: React.FC<CreateBookFormProps> = ({ onCreate, onClose }) => {
  const [title, setTitle] = React.useState("");
  const [genre, setGenre] = React.useState("ハイファンタジー (R15)");
  const [concept, setConcept] = React.useState("");
  const [synopsis, setSynopsis] = React.useState("");
  const [target_eps, setTargetEps] = React.useState(10);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const genres = [
    "ハイファンタジー (R15)",
    "ダークファンタジー",
    "異世界転生・転移",
    "恋愛・ラブコメ",
    "SF・近未来",
    "現代・日常",
    "ミステリー・サスペンス",
    "ホラー・オカルト",
    "歴史・時代",
    "その他",
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setIsSubmitting(true);
    onCreate({ title: title.trim(), genre, concept, synopsis, target_eps });
    setIsSubmitting(false);
  };

  return (
    <form onSubmit={handleSubmit} className="bookshelf-modal__create-form">
      <div className="bookshelf-modal__create-icon">＋</div>
      <h3 className="bookshelf-modal__create-title">新規作品作成</h3>
      <div className="bookshelf-modal__form-group">
        <label htmlFor="book-title">タイトル *</label>
        <input
          id="book-title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="作品タイトルを入力"
          required
          maxLength={100}
        />
      </div>
      <div className="bookshelf-modal__form-group">
        <label htmlFor="book-genre">ジャンル</label>
        <select
          id="book-genre"
          value={genre}
          onChange={(e) => setGenre(e.target.value)}
        >
          {genres.map((g) => (
            <option key={g} value={g}>{g}</option>
          ))}
        </select>
      </div>
      <div className="bookshelf-modal__form-group">
        <label htmlFor="book-concept">コンセプト</label>
        <textarea
          id="book-concept"
          value={concept}
          onChange={(e) => setConcept(e.target.value)}
          placeholder="作品のコアとなるアイデア（例：異世界でチート能力を持つ主人公が冒険する）"
          rows={3}
          maxLength={500}
        />
      </div>
      <div className="bookshelf-modal__form-group">
        <label htmlFor="book-synopsis">あらすじ</label>
        <textarea
          id="book-synopsis"
          value={synopsis}
          onChange={(e) => setSynopsis(e.target.value)}
          placeholder="物語の概要"
          rows={3}
          maxLength={1000}
        />
      </div>
      <div className="bookshelf-modal__form-group">
        <label htmlFor="book-target-eps">目標話数</label>
        <input
          id="book-target-eps"
          type="number"
          value={target_eps}
          onChange={(e) => setTargetEps(parseInt(e.target.value) || 10)}
          min={1}
          max={100}
        />
      </div>
      <button
        type="submit"
        className="btn btn-primary bookshelf-modal__create-btn"
        disabled={isSubmitting || !title.trim()}
      >
        {isSubmitting ? "作成中..." : "作成して選択"}
      </button>
    </form>
  );
};