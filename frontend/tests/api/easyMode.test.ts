import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import {
  generateContent,
  exportPackage,
  pollGenerationStatus,
  exportPackageWithData,
  generateGachaPlans,
  generateDigest,
  promoteToStudio,
} from "../../src/api/easyMode";

const server = setupServer(
  http.post("/easy_mode/generate", () => {
    return HttpResponse.json({
      output: "output",
      completion_time_ms: 0,
      error: "",
      suggestions: [],
    });
  }),
  http.get("/easy_mode/status/:taskId", () => {
    return HttpResponse.json({
      task_id: "t123",
      status: "completed",
      result: { output: "done" },
    });
  }),
  http.get("/easy_mode/export/:id", () => {
    return new HttpResponse(
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
      character_params: { name: "hero", personality: "", ability: "", genre: "" },
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
        character_params: { name: "hero", personality: "", ability: "", genre: "" },
        content_length_limit: 2000,
      })
    ).rejects.toThrow();
  });

  it("pollGenerationStatus returns status on 200", async () => {
    const result = await pollGenerationStatus("t123");
    expect(result.task_id).toBe("t123");
    expect(result.status).toBe("completed");
  });

  it("pollGenerationStatus throws on 500", async () => {
    server.use(
      http.get("/easy_mode/status/:taskId", () => {
        return new HttpResponse(null, { status: 500 });
      })
    );
    await expect(pollGenerationStatus("t123")).rejects.toThrow();
  });

  it("exportPackage returns blob + filename", async () => {
    const result = await exportPackage(1);
    expect(result.zipBlob).toBeInstanceOf(Blob);
    expect(result.filename).toBe("export_1.zip");
  });

  it("exportPackage falls back to default filename when header missing", async () => {
    server.use(
      http.get("/easy_mode/export/:id", () => {
        return new HttpResponse(new Blob(["zip"]));
      })
    );

    const result = await exportPackage(1);
    expect(result.filename).toBe("export_1.zip");
  });

  it("exportPackageWithData sends payload and returns blob + filename", async () => {
    server.use(
      http.post("/easy_mode/export-with-data", () => {
        return new HttpResponse(
          new Blob(["zip_with_data"]),
          { headers: { "Content-Disposition": 'attachment; filename="export_custom.zip"' } }
        );
      })
    );

    const result = await exportPackageWithData(1, {
      title: "テスト作品",
      current_text: "最新の本文",
    });
    expect(result.zipBlob).toBeInstanceOf(Blob);
    expect(result.filename).toBe("export_custom.zip");
  });

  it("generateGachaPlans returns GachaResponse on 200", async () => {
    server.use(
      http.post("/easy_mode/gacha", () => {
        return HttpResponse.json({
          request_id: "gacha-req-1",
          plans: [
            {
              plan_id: "p1",
              plan_type: "royal",
              title: "王道勇者譚",
              logline: "勇者が立ち上がる",
              protagonist_summary: "熱血",
              charm_point: "胸熱展開",
            },
          ],
        });
      })
    );

    const res = await generateGachaPlans({ genre: "ファンタジー", keywords: ["剣", "魔法"] });
    expect(res.request_id).toBe("gacha-req-1");
    expect(res.plans[0].title).toBe("王道勇者譚");
  });

  it("generateDigest returns DigestResponse on 200", async () => {
    server.use(
      http.post("/easy_mode/digest", () => {
        return HttpResponse.json({
          book_id: "book-100",
          title: "ダイジェスト作品",
          synopsis: "あらすじ",
          episode_1_text: "第1話本文",
          climax_preview_text: "見せ場",
          status: "completed",
        });
      })
    );

    const res = await generateDigest({ request_id: "gacha-req-1", selected_plan_id: "p1" });
    expect(res.book_id).toBe("book-100");
    expect(res.episode_1_text).toBe("第1話本文");
  });

  it("promoteToStudio returns PromotionResponse on 200", async () => {
    server.use(
      http.post("/easy_mode/promote", () => {
        return HttpResponse.json({
          success: true,
          redirect_url: "/studio?book_id=book-100",
          state_token: "token-123",
        });
      })
    );

    const res = await promoteToStudio({ book_id: "book-100" });
    expect(res.success).toBe(true);
    expect(res.redirect_url).toContain("/studio");
  });

  it("throws when network fails", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new TypeError("offline")));

    await expect(
      generateContent({
        chapter_history: [],
        current_chapter: "",
        character_params: { name: "", personality: "", ability: "", genre: "" },
        content_length_limit: 10,
      })
    ).rejects.toThrow(TypeError);
  });
});

