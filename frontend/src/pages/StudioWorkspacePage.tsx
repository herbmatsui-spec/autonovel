import React, { useEffect } from "react";
import { useParams } from "react-router-dom";
import { StudioWorkspace } from "../components/studio/StudioWorkspace";
import { useModal } from "../context/ModalContext";
import { useNovelContext } from "../context/NovelContext";

export interface StudioWorkspacePageProps {
  onMessage?: (msg: string) => void;
}

export function StudioWorkspacePage({ onMessage }: StudioWorkspacePageProps) {
  const { bookId } = useParams<{ bookId?: string }>();
  const { setSelectedBookId } = useNovelContext();
  const { openModal } = useModal();

  useEffect(() => {
    if (bookId) {
      const parsedId = parseInt(bookId, 10);
      if (!isNaN(parsedId)) {
        setSelectedBookId(parsedId);
      }
    }
  }, [bookId, setSelectedBookId]);

  return (
    <div data-testid="studio-workspace-page">
      <StudioWorkspace
        onMessage={onMessage}
        onOpenGraph={() => openModal("graph")}
      />
    </div>
  );
}

export default StudioWorkspacePage;
