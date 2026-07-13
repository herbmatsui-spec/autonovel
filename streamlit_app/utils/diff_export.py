from typing import Dict, Any

def export_for_human_polish(chapter: Dict[str, Any]) -> str:
    """
    生成稿、監査メモ、改善案を人間が編集しやすいMarkdown形式で出力する。
    """
    content = chapter.get("content", "本文なし")
    audit_memo = chapter.get("audit_memo", "監査メモなし")
    improvement = chapter.get("improvement_to_95", "改善案なし")
    score = chapter.get("audit_score", 0)

    markdown = f"""# ✍️ 執筆・修正用ワークシート
## 📊 品質スコア: {score}

### 🛠 改善の方向性 (95点超えへの道)
{improvement}

---

### 📝 生成原稿
{content}

---

### ⚖️ 監査ログ・詳細メモ
{audit_memo}

---
**編集指示**: 上記の改善案に基づき、特に「読者の情緒を破壊する一文」と「末尾のフック」を強化して仕上げてください。
"""
    return markdown
