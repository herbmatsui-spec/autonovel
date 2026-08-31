import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ExportPanel from "../../src/components/ExportPanel";

const server = setupServer(
  http.get("/easy_mode/export/:id", () => {
    return new HttpResponse(
      new Blob(["zip"]),
      { headers: { "Content-Disposition": 'attachment; filename="export_1.zip"' } }
    );
  })
);

const defaultProps = {
  output: "",
  suggestions: [] as string[],
  onExportMessage: () => {},
};

describe("ExportPanel", () => {
  server.listen();

  beforeAll(() => {
    window.URL.createObjectURL = vi.fn(() => "blob:http://localhost/dummy");
    window.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    server.resetHandlers();
    vi.clearAllMocks();
  });

  afterAll(() => server.close());

  it("renders export button", () => {
    render(<ExportPanel {...defaultProps} />);
    expect(screen.getByText(/納品パッケージ/)).toBeInTheDocument();
  });

  it("triggers download on click", async () => {
    render(<ExportPanel {...defaultProps} />);
    const user = userEvent.setup();
    await user.click(screen.getByText(/納品パッケージ/));
  });

  it("shows success message on download", async () => {
    const onExportMessage = vi.fn();
    render(<ExportPanel {...defaultProps} onExportMessage={onExportMessage} />);
    const user = userEvent.setup();
    await user.click(screen.getByText(/納品パッケージ/));
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
    await user.click(screen.getByText(/納品パッケージ/));
    expect(onExportMessage).toHaveBeenCalledWith(expect.stringContaining("エラー"));
  });
});
