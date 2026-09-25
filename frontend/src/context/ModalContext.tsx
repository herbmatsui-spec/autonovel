import React, { createContext, useContext, useState, useCallback, ReactNode } from "react";

export type ModalType =
  | "graph"
  | "media"
  | "config"
  | "bookshelf"
  | "transitionOverlay"
  | "wizard"
  | "chapterDrawer";

export interface ModalContextType {
  openModal: (type: ModalType) => void;
  closeModal: (type: ModalType) => void;
  isOpen: (type: ModalType) => boolean;
  closeAll: () => void;
  // Explicit convenient flags & setters
  showGraph: boolean;
  setShowGraph: (show: boolean) => void;
  showMedia: boolean;
  setShowMedia: (show: boolean) => void;
  showConfig: boolean;
  setShowConfig: (show: boolean) => void;
  showBookshelf: boolean;
  setShowBookshelf: (show: boolean) => void;
  showTransitionOverlay: boolean;
  setShowTransitionOverlay: (show: boolean) => void;
  showWizardWorkflow: boolean;
  setShowWizardWorkflow: (show: boolean) => void;
  isChapterDrawerOpen: boolean;
  setIsChapterDrawerOpen: (show: boolean) => void;
}

const ModalContext = createContext<ModalContextType | undefined>(undefined);

export function ModalProvider({ children }: { children: ReactNode }) {
  const [modals, setModals] = useState<Record<ModalType, boolean>>({
    graph: false,
    media: false,
    config: false,
    bookshelf: false,
    transitionOverlay: false,
    wizard: false,
    chapterDrawer: false,
  });

  const openModal = useCallback((type: ModalType) => {
    setModals((prev) => ({ ...prev, [type]: true }));
  }, []);

  const closeModal = useCallback((type: ModalType) => {
    setModals((prev) => ({ ...prev, [type]: false }));
  }, []);

  const isOpen = useCallback(
    (type: ModalType) => Boolean(modals[type]),
    [modals]
  );

  const closeAll = useCallback(() => {
    setModals({
      graph: false,
      media: false,
      config: false,
      bookshelf: false,
      transitionOverlay: false,
      wizard: false,
      chapterDrawer: false,
    });
  }, []);

  const setSpecific = useCallback((type: ModalType, val: boolean) => {
    setModals((prev) => ({ ...prev, [type]: val }));
  }, []);

  const value: ModalContextType = {
    openModal,
    closeModal,
    isOpen,
    closeAll,
    showGraph: modals.graph,
    setShowGraph: (val) => setSpecific("graph", val),
    showMedia: modals.media,
    setShowMedia: (val) => setSpecific("media", val),
    showConfig: modals.config,
    setShowConfig: (val) => setSpecific("config", val),
    showBookshelf: modals.bookshelf,
    setShowBookshelf: (val) => setSpecific("bookshelf", val),
    showTransitionOverlay: modals.transitionOverlay,
    setShowTransitionOverlay: (val) => setSpecific("transitionOverlay", val),
    showWizardWorkflow: modals.wizard,
    setShowWizardWorkflow: (val) => setSpecific("wizard", val),
    isChapterDrawerOpen: modals.chapterDrawer,
    setIsChapterDrawerOpen: (val) => setSpecific("chapterDrawer", val),
  };

  return <ModalContext.Provider value={value}>{children}</ModalContext.Provider>;
}

export function useModal(): ModalContextType {
  const context = useContext(ModalContext);
  if (!context) {
    throw new Error("useModal must be used within a ModalProvider");
  }
  return context;
}
