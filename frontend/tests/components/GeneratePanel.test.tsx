import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NovelProvider } from "../../src/context/NovelContext";
import GeneratePanel from "../../src/components/GeneratePanel";

const server = setupServer(
  http.get("/api/styles/presets", () => {
    return HttpResponse.json([
      { id: "cheat_tensei", name: "チート転生・痛快テンポ", genre: "異世界転生" },
      { id: "zarma", name: "ざまぁ・スカッと展開", genre: "追放・ざまぁ" },
    ]);
  }),
  http.post("/easy_mode/generate", () => {
    return HttpResponse.json({ output: "AI出力", suggestions: ["提案1", "提案2"] });
  }),
  http.get("/easy_mode/status/:taskId", () => {
    return HttpResponse.json({
      task_id: "task-1",
      status: "completed",
      result: { output: "ポーリング完了本文", suggestions: ["次話提案"] },
    });
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
    render(
      <NovelProvider>
        <GeneratePanel onGenerated={onGenerated} onMessage={onMessage} />
      </NovelProvider>
    );

  it("renders form and button", () => {
    renderPanel();
    expect(screen.getByText(/かんたん執筆開始/)).toBeInTheDocument();
    expect(screen.getByText("主人公の名前")).toBeInTheDocument();
  });

  it("submits generation and shows output + suggestions", async () => {
    renderPanel();
    const user = userEvent.setup();
    await user.click(screen.getByText(/かんたん執筆開始/));
    expect(onGenerated).toHaveBeenCalledWith(
      expect.stringContaining("AI出力"),
      expect.arrayContaining([expect.stringContaining("提案1")])
    );
    expect(onMessage).toHaveBeenCalledWith(expect.stringContaining("完了"));
  });

  it("polls task until completed when task_id is returned", async () => {
    server.use(
      http.post("/easy_mode/generate", () => {
        return HttpResponse.json({
          task_id: "task-1",
          output: "",
          suggestions: [],
        });
      })
    );
    renderPanel();
    const user = userEvent.setup();
    await user.click(screen.getByText(/かんたん執筆開始/));
    expect(onGenerated).toHaveBeenCalledWith(
      "ポーリング完了本文",
      ["次話提案"]
    );
  });

  it("handles failed polling status", async () => {
    server.use(
      http.post("/easy_mode/generate", () => {
        return HttpResponse.json({
          task_id: "task-err",
          output: "",
          suggestions: [],
        });
      }),
      http.get("/easy_mode/status/task-err", () => {
        return HttpResponse.json({
          task_id: "task-err",
          status: "failed",
          error: "LLM error occurred",
        });
      })
    );
    renderPanel();
    const user = userEvent.setup();
    await user.click(screen.getByText(/かんたん執筆開始/));
    expect(onMessage).toHaveBeenCalledWith(expect.stringContaining("LLM error occurred"));
  });

  it("shows error message on 500", async () => {
    server.use(
      http.post("/easy_mode/generate", () => {
        return new HttpResponse(null, { status: 500 });
      })
    );
    renderPanel();
    const user = userEvent.setup();
    await user.click(screen.getByText(/かんたん執筆開始/));
    expect(onMessage).toHaveBeenCalledWith(expect.stringContaining("エラー"));
  });

  it("shows loading state while submitting", async () => {
    server.use(
      http.post("/easy_mode/generate", async () => {
        await new Promise((resolve) => setTimeout(resolve, 300));
        return HttpResponse.json({ output: "ok", suggestions: [] });
      })
    );
    renderPanel();
    fireEvent.click(screen.getByText(/かんたん執筆開始/));
    expect(screen.getByText(/執筆中/)).toBeInTheDocument();
  });
});
