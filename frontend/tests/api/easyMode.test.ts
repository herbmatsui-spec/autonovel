import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { generateContent, exportPackage } from "../../src/api/easyMode";

const server = setupServer(
  http.post("/easy_mode/generate", () => {
    return HttpResponse.json({ output: "output", suggestions: [] });
  }),
  http.get("/easy_mode/export/:id", () => {
    return HttpResponse(
      new Blob(["zip"]),
      { headers: { "Content-Disposition": 'attachment; filename="export_1.zip"' } }
    );
  })
);

describe("easyMode API client", () => {
  server.listen();

  afterEach(() => server.resetHandlers());

  afterAll(() => server.close());

  it("generateContent returns GenerationResponse on 200", async () => {
    const result = await generateContent({
      chapter_history: ["a"],
      current_chapter: "b",
      character_params: {},
      content_length_limit: 2000,
    });
    expect(result.output).toBe("output");
    expect(result.completion_time_ms).toBe(0);
  });

  it("generateContent throws on 500", async () => {
    server.use(
      http.post("/easy_mode/generate", () => {
        return new HttpResponse(null, { status: 500 });
      })
    );

    await expect(
      generateContent({
        chapter_history: ["a"],
        current_chapter: "b",
        character_params: {},
        content_length_limit: 2000,
      })
    ).rejects.toThrow();
  });

  it("exportPackage returns blob + filename", async () => {
    const result = await exportPackage(1);
    expect(result.zipBlob).toBeInstanceOf(Blob);
    expect(result.filename).toBe("export_1.zip");
  });

  it("exportPackage falls back to default filename when header missing", async () => {
    server.use(
      http.get("/easy_mode/export/:id", () => {
        return HttpResponse(new Blob(["zip"]));
      })
    );

    const result = await exportPackage(1);
    expect(result.filename).toBe("export_1.zip");
  });

  it("throws when network fails", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new TypeError("offline")));

    await expect(
      generateContent({
        chapter_history: [],
        current_chapter: "",
        character_params: {},
        content_length_limit: 10,
      })
    ).rejects.toThrow(TypeError);
  });
});
