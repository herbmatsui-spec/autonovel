from src.services.exporters.ruby_parser import parse_bouten, parse_ruby_to_xhtml
from src.services.exporters.tcy_formatter import apply_tatechuyoko
from src.services.exporters.text_sanitizer import escape_xhtml_text, sanitize_novel_text


class EpubContentBuilder:
    """XHTMLエピソード本文および挿絵ページの生成器 (Steps 42, 46)。"""

    @staticmethod
    def build_chapter_xhtml(
        chapter_title: str,
        content: str,
        chapter_index: int = 1,
        css_rel_path: str = "../style/vertical.css",
    ) -> str:
        sanitized = sanitize_novel_text(content)
        paragraphs = [p.strip() for p in sanitized.splitlines() if p.strip()]

        body_lines = [f"<h1>{escape_xhtml_text(chapter_title)}</h1>", ""]
        for p in paragraphs:
            escaped = escape_xhtml_text(p)
            with_ruby = parse_ruby_to_xhtml(escaped)
            with_bouten = parse_bouten(with_ruby)
            formatted = apply_tatechuyoko(with_bouten)

            if p.startswith(("「", "『", "（", "(")):
                body_lines.append(f'<p class="dialogue">{formatted}</p>')
            else:
                body_lines.append(f"<p>{formatted}</p>")

        content_html = "\n".join(body_lines)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ja" class="vrtl">
<head>
<meta charset="UTF-8" />
<title>{escape_xhtml_text(chapter_title)}</title>
<link rel="stylesheet" type="text/css" href="{css_rel_path}" />
</head>
<body class="p-text">
<div class="main">
{content_html}
</div>
</body>
</html>"""

    @staticmethod
    def build_illustration_xhtml(
        image_rel_path: str,
        title: str = "挿絵",
        css_rel_path: str = "../style/vertical.css",
    ) -> str:
        """口絵・章間挿絵の専用見開きレイアウト (Step 46)。"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ja">
<head>
<meta charset="UTF-8" />
<title>{escape_xhtml_text(title)}</title>
<link rel="stylesheet" type="text/css" href="{css_rel_path}" />
</head>
<body class="p-image">
<div class="illustration-container">
    <img src="{image_rel_path}" alt="{escape_xhtml_text(title)}" />
</div>
</body>
</html>"""
