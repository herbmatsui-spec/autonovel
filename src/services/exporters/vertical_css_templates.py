"""商用ライトノベル専用 縦書きCSSテンプレート (Step 37)。"""

VERTICAL_EPUB_CSS = """@charset "utf-8";

html {
    writing-mode: vertical-rl;
    -webkit-writing-mode: vertical-rl;
    line-break: strict;
    word-break: normal;
}

body {
    font-family: "Hiragino Mincho ProN", "Yu Mincho", "Noto Serif CJK JP", serif;
    font-size: 100%;
    line-height: 1.85;
    margin: 0;
    padding: 0;
}

h1, h2, h3 {
    font-family: "Hiragino Kaku Gothic ProN", "Yu Gothic", "Noto Sans CJK JP", sans-serif;
    font-weight: bold;
    margin-right: 1.5em;
    margin-left: 1em;
}

h1 {
    font-size: 1.8em;
}

h2 {
    font-size: 1.4em;
}

p {
    text-indent: 1em;
    margin: 0;
    padding: 0;
}

p.dialogue {
    text-indent: 0;
}

/* ルビ */
ruby {
    ruby-align: center;
}

ruby rt {
    font-size: 0.5em;
}

/* 傍点（ごま点・セサミ） */
.bouten {
    text-emphasis-style: sesame;
    -webkit-text-emphasis-style: sesame;
}

/* 縦中横 */
.tcy {
    text-combine-upright: all;
    -webkit-text-combine: horizontal;
    -ms-text-combine-horizontal: all;
}

/* 改ページ */
.pagebreak {
    page-break-before: always;
    break-before: page;
}

/* 挿絵画像 */
.illustration-container {
    text-align: center;
    margin: 0;
    padding: 0;
    page-break-before: always;
    break-before: page;
}

.illustration-container img {
    max-height: 100%;
    max-width: 100%;
    object-fit: contain;
}
"""
