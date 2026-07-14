import { create } from 'zustand';
import { Book, Chapter, Plot, Bible } from '../types';

interface BookState {
  selectedBook: Book | null;
  chapters: Chapter[];
  plots: Plot[];
  bible: Bible | null;
  setSelectedBook: (book: Book | null) => void;
  setChapters: (chapters: Chapter[]) => void;
  setPlots: (plots: Plot[]) => void;
  setBible: (bible: Bible | null) => void;
  clearBookData: () => void;
}

export const useBookStore = create<BookState>((set) => ({
  selectedBook: null,
  chapters: [],
  plots: [],
  bible: null,
  setSelectedBook: (book) => set({ selectedBook: book }),
  setChapters: (chapters) => set({ chapters }),
  setPlots: (plots) => set({ plots }),
  setBible: (bible) => set({ bible }),
  clearBookData: () =>
    set({
      selectedBook: null,
      chapters: [],
      plots: [],
      bible: null,
    }),
}));
