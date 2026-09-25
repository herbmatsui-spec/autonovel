import React from "react";
import { useNavigate } from "react-router-dom";
import GeneratePanel from "../components/GeneratePanel";
import ExportPanel from "../components/ExportPanel";

export interface EasyModePageProps {
  onMessage?: (msg: string) => void;
}

export function EasyModePage({ onMessage }: EasyModePageProps) {
  const navigate = useNavigate();

  const handleMessage = (msg: string) => {
    onMessage?.(msg);
  };

  return (
    <main className="main-grid" data-testid="easy-mode-page">
      <GeneratePanel onMessage={handleMessage} />
      <ExportPanel
        onExportMessage={handleMessage}
        onPromoteToStudio={() => navigate("/studio")}
      />
    </main>
  );
}

export default EasyModePage;
