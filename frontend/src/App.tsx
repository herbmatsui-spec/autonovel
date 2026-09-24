import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { NovelProvider } from "./context/NovelContext";
import { ModalProvider } from "./context/ModalContext";
import { AppLayout } from "./components/layout/AppLayout";
import { GlobalModals } from "./components/modals/GlobalModals";
import { EasyModePage } from "./pages/EasyModePage";
import { StudioWorkspacePage } from "./pages/StudioWorkspacePage";
import { WizardWorkflowPage } from "./pages/WizardWorkflowPage";

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <NovelProvider>
      <ModalProvider>{children}</ModalProvider>
    </NovelProvider>
  );
}

export function App() {
  return (
    <AppProviders>
      <BrowserRouter>
        <AppLayout>
          <Routes>
            <Route path="/" element={<EasyModePage />} />
            <Route path="/studio" element={<StudioWorkspacePage />} />
            <Route path="/studio/:bookId" element={<StudioWorkspacePage />} />
            <Route path="/wizard" element={<WizardWorkflowPage />} />
          </Routes>
        </AppLayout>
        <GlobalModals />
      </BrowserRouter>
    </AppProviders>
  );
}

export default App;
