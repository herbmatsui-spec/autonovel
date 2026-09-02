import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ExportPanel from "../../src/components/ExportPanel";
import { NovelProvider } from "../../src/context/NovelContext";
import * as easyModeApi from "../../src/api/easyMode";

vi.mock("../../src/api/easyMode", () => ({
  exportPackageWithData: vi.fn().mockResolvedValue({
    zipBlob: new Blob(["dummy zip content"], { type: "application/zip" }),
    filename: "export_1.zip",
  }),
  promoteToStudio: vi.fn().mockResolvedValue({
    success: true,
    redirect_url: "/advanced/1",
    state_token: "mock_token_123",
  }),
  exportPackage: vi.fn().mockResolvedValue({
    zipBlob: new Blob(["dummy zip content"], { type: "application/zip" }),
    filename: "export_1.zip",
  }),
}));

describe("ExportPanel component", () => {
  it("exports package with current text and settings", async () => {
    const onExportMessage = vi.fn();
    const user = userEvent.setup();

    render(
      <NovelProvider>
        <ExportPanel onExportMessage={onExportMessage} />
      </NovelProvider>
    );

    const exportBtn = screen.getByTestId("btn-export-zip");
    await user.click(exportBtn);

    expect(easyModeApi.exportPackageWithData).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        title: expect.stringContaining("アルト"),
        genre: "ハイファンタジー (R15)",
        character: expect.objectContaining({ name: "アルト" }),
      })
    );
  });

  it("calls promoteToStudio when promote button is clicked", async () => {
    const onExportMessage = vi.fn();
    const onPromoteToStudio = vi.fn();
    const user = userEvent.setup();

    render(
      <NovelProvider>
        <ExportPanel
          onExportMessage={onExportMessage}
          onPromoteToStudio={onPromoteToStudio}
        />
      </NovelProvider>
    );

    const promoteBtn = screen.getByTestId("btn-promote-studio");
    await user.click(promoteBtn);

    expect(easyModeApi.promoteToStudio).toHaveBeenCalledWith({ book_id: "1" });
    expect(onExportMessage).toHaveBeenCalledWith(
      expect.stringContaining("上級者 Studio へ昇格しました")
    );
    expect(onPromoteToStudio).toHaveBeenCalled();
  });
});
