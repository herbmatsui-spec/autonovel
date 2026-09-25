import React from "react";
import { RouteObject } from "react-router-dom";
import { EasyModePage } from "./pages/EasyModePage";
import { StudioWorkspacePage } from "./pages/StudioWorkspacePage";
import { WizardWorkflowPage } from "./pages/WizardWorkflowPage";

export const routes: RouteObject[] = [
  { path: "/", element: <EasyModePage /> },
  { path: "/studio/:bookId?", element: <StudioWorkspacePage /> },
  { path: "/wizard", element: <WizardWorkflowPage /> },
];

export default routes;
