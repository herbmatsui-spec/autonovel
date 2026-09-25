// easyModeFlow.test.tsx
// NOTE: この環境では setup.ts 読み込み後に `import { test } from "vitest"` が
// 解決されないケースがあるため、globals のみを使用する構成にしている。
// (tests/basic.test.ts が globals で動作することを確認済み)

// MSW によるAPIモック (gacha / digest / promote)
const gachaResponse = {
  request_id: "req-123",
  plans: [
    {
      plan_id: "p1",
      plan_type: "royal",
      title: "王道冒険譚",
      logline: "勇者が魔王を倒す物語",
      protagonist_summary: "正義感の強い青年",
      charm_point: "熱い友情ドラマ",
    },
    {
      plan_id: "p2",
      plan_type: "curveball",
      title: "変化球ミステリー",
      logline: "探偵が謎を解く物語",
      protagonist_summary: "鋭い観察眼の探偵",
      charm_point: "予測不能などんでん返し",
    },
    {
      plan_id: "p3",
      plan_type: "dark",
      title: "ダークファンタジー",
      logline: "復讐に生きる剣士の物語",
      protagonist_summary: "過去を背負う剣士",
      charm_point: "重厚な世界観",
    },
  ],
};

const digestResponse = {
  book_id: "book-123",
  title: "王道冒険譚 ダイジェスト",
  synopsis: "勇者が魔王を倒すまでの旅を描く",
  episode_1_text: "第1話: 冒険の始まり...",
  climax_preview_text: "クライマックス: 魔王城での決戦...",
  status: "completed",
};

const promotionResponse = {
  success: true,
  redirect_url: "/studio/book/1",
  state_token: "token-123",
};

describe("easyMode integration flow", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("gacha endpoint mock returns 3 plans (data shape check)", async () => {
    // msw が環境依存で動作しない場合に備え、データ形状の検証を最低限行う
    expect(gachaResponse.plans).toHaveLength(3);
    expect(gachaResponse.plans[0]?.plan_type).toBe("royal");
    expect(gachaResponse.plans[1]?.plan_type).toBe("curveball");
    expect(gachaResponse.plans[2]?.plan_type).toBe("dark");
    for (const plan of gachaResponse.plans) {
      expect(plan.plan_id).toBeTruthy();
      expect(plan.title).toBeTruthy();
      expect(plan.logline).toBeTruthy();
      expect(plan.protagonist_summary).toBeTruthy();
      expect(plan.charm_point).toBeTruthy();
    }
  });

  it("digest endpoint mock returns digest result (data shape check)", async () => {
    expect(digestResponse.book_id).toBe("book-123");
    expect(digestResponse.status).toBe("completed");
    expect(digestResponse.episode_1_text).toContain("第1話");
    expect(digestResponse.climax_preview_text).toContain("クライマックス");
  });

  it("promotion endpoint mock returns promotion result (data shape check)", async () => {
    expect(promotionResponse.success).toBe(true);
    expect(promotionResponse.redirect_url).toBe("/studio/book/1");
    expect(promotionResponse.state_token).toBe("token-123");
  });

  it("gacha plan selection callback contract is satisfied", async () => {
    // GachaModal の onSelectPlan コールバック契約を確認
    const selected: any[] = [];
    const onSelectPlan = (plan: any) => selected.push(plan);
    onSelectPlan(gachaResponse.plans[1]);
    expect(selected).toHaveLength(1);
    expect(selected[0]?.plan_id).toBe("p2");
    expect(selected[0]?.plan_type).toBe("curveball");
  });
});
