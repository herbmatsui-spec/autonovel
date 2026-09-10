import "@testing-library/jest-dom/vitest";
import { beforeAll, afterEach, afterAll, vi } from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

const worker = setupServer(
  // Book endpoints
  http.get("/api/books/:id", ({ params }) => {
    const { id } = params;
    return HttpResponse.json({
      id: Number(id),
      title: `Test Book ${id}`,
      author: "Test Author",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
  }),
  http.get("/api/books", () => {
    return HttpResponse.json([
      { id: 1, title: "Test Book 1", author: "Test Author", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
      { id: 2, title: "Test Book 2", author: "Test Author", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    ]);
  }),
  // Orchestrated endpoints
  http.post("/orchestrated/generate", () => {
    return HttpResponse.json({ task_id: "mock-orch-task", status: "pending", message: "OK" });
  }),
  http.get("/orchestrated/status/:task_id", ({ params }) => {
    const { task_id } = params;
    if (task_id === "mock-orch-task") {
      return HttpResponse.json({ task_id, status: "completed", result: { output: "Generated" } });
    }
    return HttpResponse.json({ task_id, status: "pending" });
  }),
  http.get("/orchestrated/events/:correlation_id", () => {
    return new HttpResponse(
      `data: ${JSON.stringify({ event: "agent_event", data: JSON.stringify({ agent: "planning", status: "running" }) })}\n\n`,
      {
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          "Connection": "keep-alive",
        },
      }
    );
  }),
  // Generate endpoints (mocked as needed)
  http.post("/api/generate", () => {
    return HttpResponse.json({ task_id: "mock-task-id" });
  }),
  http.get("/api/tasks/:task_id", ({ params }) => {
    const { task_id } = params;
    if (task_id === "mock-task-id") {
      return HttpResponse.json({ status: "completed", result: "Generated text", suggestions: [] });
    }
    return HttpResponse.json({ status: "processing" });
  }),
  // EasyMode endpoints (for easyMode API client)
  http.post("/easy_mode/generate", () => {
    return HttpResponse.json({ task_id: "mock-easy-task", output: "Generated text", completion_time_ms: 100, error: "", suggestions: [] });
  }),
  http.get("/easy_mode/status/:task_id", ({ params }) => {
    const { task_id } = params;
    if (task_id === "mock-easy-task") {
      return HttpResponse.json({ status: "completed", result: JSON.stringify({ output: "Generated text", suggestions: [] }) });
    }
    return HttpResponse.json({ status: "pending" });
  }),
  http.get("/easy_mode/export/:book_id", () => {
    return new HttpResponse(new Blob(["mock zip"]), {
      headers: { "Content-Disposition": "attachment; filename=mock.zip" }
    });
  }),
  http.post("/easy_mode/export-with-data", () => {
    return new HttpResponse(new Blob(["mock zip"]), {
      headers: { "Content-Disposition": "attachment; filename=mock.zip" }
    });
  }),
  http.post("/easy_mode/gacha", () => {
    return HttpResponse.json({ plans: [] });
  }),
  http.post("/easy_mode/digest", () => {
    return HttpResponse.json({ digest: "" });
  }),
  http.post("/easy_mode/promote", () => {
    return HttpResponse.json({ success: true, redirect_url: "/studio", state_token: "mock-token" });
  }),
  http.post("/easy_mode/reverse-generate", () => {
    return HttpResponse.json({ arcs: [], episodes: [] });
  }),
  // EasyMode endpoints
  http.post("/api/easy_mode/generate_gacha_plans", () => {
    return HttpResponse.json({ plans: [] });
  }),
  http.post("/api/easy_mode/generate_digest", () => {
    return HttpResponse.json({ digest: "" });
  }),
  // Editor endpoints
  http.post("/api/editor/assist", () => {
    return HttpResponse.json({ result_text: "Assisted text", diff_summary: "Assisted" });
  }),
  // Branches endpoints
  http.get("/api/branches/:bookId/fork", ({ params }) => {
    const { bookId } = params;
    return HttpResponse.json({ id: 2, name: "Test Branch", fork_ep_num: 1 });
  }),
  http.get("/api/branches/:bookId", ({ params }) => {
    const { bookId } = params;
    return HttpResponse.json({ id: 1, name: "Main", book_id: Number(bookId) });
  }),
  http.get("/api/branches/diff", () => {
    return HttpResponse.json({ diff_unified: "", diff_side_by_side: { left: [], right: [] } });
  }),
);

beforeAll(() => {
  if (typeof window !== "undefined") {
    window.URL.createObjectURL = vi.fn(() => "blob:http://localhost/mock");
    window.URL.revokeObjectURL = vi.fn();
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
    Element.prototype.scrollIntoView = vi.fn();
  }
  worker.listen();
});

afterEach(() => {
  vi.clearAllMocks();
  worker.resetHandlers();
});

afterAll(() => {
  worker.close();
});

afterEach(() => {
  vi.clearAllMocks();
  worker.resetHandlers();
});

afterAll(() => {
  worker.close();
});
