"""Commercial Vertical EPUB 3 CSS Styler for Kindle (KDP) and Rakuten Kobo (v5.0 Step 15)."""
from __future__ import annotations

COMMERCIAL_VERTICAL_CSS = """@charset "UTF-8";

html {
  writing-mode: vertical-rl;
  -webkit-writing-mode: vertical-rl;
  -epub-writing-mode: vertical-rl;
  font-family: "Hiragino Mincho ProN", "Yu Mincho", serif;
  font-size: 100%;
  line-height: 1.85;
}

body {
  margin: 0;
  padding: 0;
}

h1, h2, h3 {
  font-family: "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif;
  margin-right: 1.5em;
  margin-left: 1.5em;
}

p {
  margin: 0;
  padding: 0;
  text-indent: 1em;
  text-align: justify;
}

p.dialogue {
  text-indent: 0;
}

p.empty-line {
  text-indent: 0;
  margin: 0;
  padding: 0;
}

/* 禁則処理 */
p, div {
  word-break: normal;
  overflow-wrap: break-word;
}

/* 圏点・傍点 */
span.bouten {
  -webkit-text-emphasis-style: sesame;
  text-emphasis-style: sesame;
}

/* 縦中横 (2桁数字・感嘆符) */
span.tcy {
  -webkit-text-combine: horizontal;
  -epub-text-combine: horizontal;
  text-combine-upright: all;
}
"""
