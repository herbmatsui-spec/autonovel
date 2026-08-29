import { create } from 'zustand';
import { Book, Chapter, Plot, Bible, AxisType, AxisState } from '../types';

const STORAGE_KEY = 'axis_lock_flags';

function loadLocks(): Record<AxisType, boolean> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // ignore
  }
  return {};
}

function saveLocks(locks: Record<AxisType, boolean>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(locks));
  } catch {
    // ignore
  }
}

const initialAxisSelections: Record<AxisType, AxisState> = {
  output_mode: { value: null, locked: false, defaultValue: null },
  theme: { value: null, locked: false, defaultValue: null },
  genre: { value: null, locked: false, defaultValue: null },
  worldview: { value: null, locked: false, defaultValue: null },
  audience: { value: null, locked: false, defaultValue: null },
  era: { value: null, locked: false, defaultValue: null },
  ending_style: { value: null, locked: false, defaultValue: null },
  narrator: { value: null, locked: false, defaultValue: null },
  characters: { value: null, locked: false, defaultValue: null },
  universal_input: { value: null, locked: false, defaultValue: null },
  supplemental_note: { value: null, locked: false, defaultValue: null },
};

interface BookState {
  selectedBook: Book | null;
  chapters: Chapter[];
  plots: Plot[];
  bible: Bible | null;
  axisSelections: Record<AxisType, AxisState>;
  setSelectedBook: (book: Book | null) => void;
  setChapters: (chapters: Chapter[]) => void;
  setPlots: (plots: Plot[]) => void;
  setBible: (bible: Bible | null) => void;
  setAxisSelection: (axis: AxisType, value: AxisState['value']) => void;
  setAxisLock: (axis: AxisType, locked: boolean) => void;
  resetAxis: (axis: AxisType) => void;
  clearBookData: () => void;
  hydrateLocks: () => void;
  syncLocksFromBook: (book: Book) => void;
  selectBook: (book: Book | null) => void;
  exportPreset: () => string;
  importPreset: (json: string) => void;
}

export const useBookStore = create<BookState>((set, get) => ({
  selectedBook: null,
  chapters: [],
  plots: [],
  bible: null,
  axisSelections: initialAxisSelections,
  setSelectedBook: (book) => set({ selectedBook: book }),
  setChapters: (chapters) => set({ chapters }),
  setPlots: (plots) => set({ plots }),
  setBible: (bible) => set({ bible }),
  setAxisSelection: (axis, value) =>
    set((state) => ({
      axisSelections: {
        ...state.axisSelections,
        [axis]: { ...state.axisSelections[axis], value },
      },
    })),
  setAxisLock: (axis, locked) =>
    set((state) => {
      const newSelections = {
        ...state.axisSelections,
        [axis]: { ...state.axisSelections[axis], locked },
      };
      // persist locks
      const locks = Object.fromEntries(
        Object.entries(newSelections).map(([k, v]) => [k, v.locked])
      );
      saveLocks(locks);
      return { axisSelections: newSelections };
    }),
  resetAxis: (axis) =>
    set((state) => ({
      axisSelections: {
        ...state.axisSelections,
        [axis]: { ...state.axisSelections[axis], value: state.axisSelections[axis].defaultValue },
      },
    })),
  clearBookData: () =>
    set({
      selectedBook: null,
      chapters: [],
      plots: [],
      bible: null,
      axisSelections: initialAxisSelections,
    }),
  hydrateLocks: () => {
    const saved = loadLocks();
    if (Object.keys(saved).length === 0) return;
    set((state) => {
      const newSelections = { ...state.axisSelections };
      for (const [axis, locked] of Object.entries(saved)) {
        if (newSelections[axis as AxisType]) {
          newSelections[axis as AxisType] = {
            ...newSelections[axis as AxisType],
            locked,
          };
        }
      }
      return { axisSelections: newSelections };
    });
  },
  syncLocksFromBook: (book) => {
    if (!book.axis_lock_flags) return;
    set((state) => {
      const newSelections = { ...state.axisSelections };
      let changed = false;
      for (const [axis, locked] of Object.entries(book.axis_lock_flags!)) {
        if (newSelections[axis as AxisType] && newSelections[axis as AxisType].locked !== locked) {
          newSelections[axis as AxisType] = {
            ...newSelections[axis as AxisType],
            locked,
          };
          changed = true;
        }
      }
      if (changed) {
        // persist merged locks
        const locks = Object.fromEntries(
          Object.entries(newSelections).map(([k, v]) => [k, v.locked])
        );
        saveLocks(locks);
      }
      return changed ? { axisSelections: newSelections } : state;
    });
  },
  selectBook: (book) => {
    const currentBook = get().selectedBook;
    if (book === null) {
      set({ selectedBook: null });
      return;
    }
    set({ selectedBook: book });
    // sync locks from book data
    get().syncLocksFromBook(book);
  },
  exportPreset: () => {
    const { axisSelections } = get();
    const preset = {
      axisSelections: Object.fromEntries(
        Object.entries(axisSelections).map(([axis, state]) => [
          axis,
          { value: state.value, locked: state.locked, defaultValue: state.defaultValue },
        ])
      ),
    };
    return JSON.stringify(preset, null, 2);
  },
  importPreset: (json: string) => {
    try {
      const preset = JSON.parse(json);
      if (!preset.axisSelections) return;
      set((state) => {
        const newSelections = { ...state.axisSelections };
        for (const [axis, data] of Object.entries(preset.axisSelections)) {
          if (newSelections[axis as AxisType]) {
            newSelections[axis as AxisType] = {
              ...newSelections[axis as AxisType],
              value: (data as any).value,
              locked: (data as any).locked,
              defaultValue: (data as any).defaultValue,
            };
          }
        }
        // persist locks
        const locks = Object.fromEntries(
          Object.entries(newSelections).map(([k, v]) => [k, v.locked])
        );
        saveLocks(locks);
        return { axisSelections: newSelections };
      });
    } catch (e) {
      console.error('Failed to import preset', e);
    }
  },
}));
