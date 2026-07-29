import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import GeneratePanel from "../../src/components/GeneratePanel";

const server = setupServer(
  http.post("/easy_mode/generate", () => {
    return HttpResponse.json({ output: "AI出力", suggestions: ["提案1", "提案2"] });
  })
);

const onGenerated = vi.fn();
const onMessage = vi.fn();

describe("GeneratePanel", () => {
  server.listen();

  beforeAll(() => {
    vi.stubGlobal("URL", URL);
  });

  afterEach(() => {
    server.resetHandlers();
    vi.clearAllMocks();
  });

  afterAll(() => server.close());

  const renderPanel = () =>
    render(<GeneratePanel onGenerated={onGenerated} onMessage={onMessage} />);

  it("renders form and button", () => {
    renderPanel();
    expect(screen.getByText("かんたん執筆開始")).toBeInTheDocument();
    expect(screen.getByText("主人公の名前")).toBeInTheDocument();
  });

  it("submits generation and shows output + suggestions", async () => {
    renderPanel();
    const user = userEvent.setup();
    await user.click(screen.getByText("かんたん執筆開始"));
    expect(onGenerated).toHaveBeenCalledWith(
      expect.stringContaining("AI出力"),
      expect.arrayContaining([expect.stringContaining("提案1")])
    );
    expect(onMessage).toHaveBeenCalledWith(expect.stringContaining("完了"));
  });

  it("shows error message on 500", async () => {
    server.use(
      http.post("/easy_mode/generate", () => {
        return new HttpResponse(null, { status: 500 });
      })
    );
    renderPanel();
    const user = userEvent.setup();
    await user.click(screen.getByText("かんたん執筆開始"));
    expect(onMessage).toHaveBeenCalledWith(expect.stringContaining("エラー"));
  });

  it("shows loading state while submitting", async () => {
    server.use(
      http.post("/easy_mode/generate", async () => {
        await new Promise((resolve) => setTimeout(resolve, 50));
        return HttpResponse.json({ output: "ok", suggestions: [] });
      })
    );
    renderPanel();
    const user = userEvent.setup();
    await user.click(screen.getByText("かんたん執筆開始"));
    expect(screen.getByText("🪄 執筆中...")).toBeInTheDocument();
  });
});
