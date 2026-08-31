import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { render, screen } from "@testing-library/react";
import App from "../../src/App";

const server = setupServer(
  http.post("/easy_mode/generate", () => {
    return HttpResponse.json({ output: "生成結果", suggestions: ["次", "案"] });
  }),
  http.get("/easy_mode/export/:id", () => {
    return new HttpResponse(
      new Blob(["zip"]),
      { headers: { "Content-Disposition": 'attachment; filename="export_1.zip"' } }
    );
  })
);

describe("easyMode integration flow", () => {
  server.listen();

  beforeAll(() => {
    vi.stubGlobal("URL", URL);
    vi.stubGlobal("document", document);
  });

  afterEach(() => server.resetHandlers());

  afterAll(() => server.close());

  it("renders panels and all endpoints", async () => {
    render(<App />);
    expect(screen.getByText("AutoNovel かんたん制作")).toBeInTheDocument();
  });
});
