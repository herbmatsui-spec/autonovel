import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ExportPanel from "../../src/components/ExportPanel";

const server = setupServer(
  http.get("/easy_mode/export/:id", () => {
    return HttpResponse(
      new Blob(["zip"]),
      { headers: { "Content-Disposition": 'attachment; filename="export_1.zip"' } }
    );
  })
);

const defaultProps = {
  output: "",
  suggestions: [],
  onExportMessage: () => {},
} as const;

describe("ExportPanel", () => {
  server.listen();

  beforeAll(() => {
    vi.stubGlobal("URL", URL);
    vi.stubGlobal("document", document);
  });

  afterEach(() => {
    server.resetHandlers();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  afterAll(() => server.close());

  it("renders export button", () => {
    render(<ExportPanel {...defaultProps} />);
    expect(screen.getByText("📦 納品パッケージ (ZIP) ダウンロード")).toBeInTheDocument();
  });

  it("triggers download on click", async () => {
    const clickSpy = vi.spyOn(document, "createElement");
    render(<ExportPanel {...defaultProps} />);
    const user = userEvent.setup();
    await user.click(screen.getByText("📦 納品パッケージ (ZIP) ダウンロード"));
    clickSpy.mockRestore();
  });

  it("shows success message on download", async () => {
    const onExportMessage = vi.fn();
    render(<ExportPanel {...defaultProps} onExportMessage={onExportMessage} />);
    const user = userEvent.setup();
    await user.click(screen.getByText("📦 納品パッケージ (ZIP) ダウンロード"));
    expect(onExportMessage).toHaveBeenCalledWith(
      expect.stringContaining("ダウンロードしました")
    );
  });

  it("shows error on 500", async () => {
    server.use(
      http.get("/easy_mode/export/:id", () => {
        return new HttpResponse(null, { status: 500 });
      })
    );
    const onExportMessage = vi.fn();
    render(<ExportPanel {...defaultProps} onExportMessage={onExportMessage} />);
    const user = userEvent.setup();
    await user.click(screen.getByText("📦 納品パッケージ (ZIP) ダウンロード"));
    expect(onExportMessage).toHaveBeenCalledWith(expect.stringContaining("エラー"));
  });
});
