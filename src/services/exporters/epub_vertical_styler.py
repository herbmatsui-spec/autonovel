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

/* 基本テキストスタイル */
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

/* 見出しスタイル */
h1, h2, h3 {
  font-family: "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif;
  margin-right: 2em;
  margin-left: 2em;
  font-weight: bold;
  line-height: 1.4;
}

h1 {
  font-size: 2em;
  margin-top: 1em;
  margin-bottom: 1em;
  text-align: center;
}

h2 {
  font-size: 1.5em;
  margin-top: 0.8em;
  margin-bottom: 0.8em;
  text-align: center;
}

h3 {
  font-size: 1.2em;
  margin-top: 0.5em;
  margin-bottom: 0.5em;
  text-align: center;
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

/* カバーページスタイル */
.cover-page {
  text-align: center;
  padding: 2em;
}

.cover-page .title {
  font-size: 2.5em;
  margin-bottom: 0.5em;
  font-weight: bold;
}

.cover-page .author {
  font-size: 1.5em;
  margin-bottom: 1em;
}

/* 中扉ページスタイル */
.middle-page {
  text-align: center;
  padding: 2em;
}

.middle-page .title {
  font-size: 2em;
  margin-bottom: 0.5em;
  font-weight: bold;
}

.middle-page .author {
  font-size: 1.3em;
  margin-bottom: 1em;
}

/* 目次ページスタイル */
.toc-page {
  padding: 1em;
}

.toc-page .toc-title {
  font-size: 1.8em;
  margin-bottom: 1em;
  text-align: center;
  font-weight: bold;
}

.toc-page .toc-item {
  margin: 0.5em 0;
  padding-left: 2em;
  text-indent: -2em;
}

/* 挿絵ページスタイル */
.illustration-page {
  text-align: center;
  padding: 2em;
}

.illustration-page .image {
  margin: 1em auto;
  max-width: 80%;
  height: auto;
}

.illustration-page .caption {
  font-size: 0.9em;
  margin-top: 0.5em;
  font-style: italic;
  text-align: center;
}

/* ナビゲーションスタイル */
nav {
  padding: 1em;
}

nav ol {
  line-height: 1.6;
}

nav li {
  margin: 0.5em 0;
  padding-left: 2em;
  text-indent: -2em;
}
"""
