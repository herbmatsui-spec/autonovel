# テスト用モック官能小説 実装計画書

## 目的

官能Aサブエージェントのテスト容易化のため、強度別・傾向別のモック官能小説テキストを作成する。

## モック一覧

| # | ファイル名 | 強度 | 傾向 | 想定テストケース |
|---|---|---|---|---|
| 1 | `mock_erotic_pure_love.md` | 3 | 純愛官能（情緒重視・同意明示） | intensity 3 の正常系、比喩密度テスト |
| 2 | `mock_erotic_taboo.md` | 4 | 背徳官能（心理葛藤・タブー） | intensity 4 の高欲望テスト、心理描写テスト |
| 3 | `mock_erotic_extreme.md` | 5 | 過激官能（感覚変容・精神溶解） | intensity 5 の極限テスト、サブビートテスト |

## 各モックに含めるべき要素

### 必須シーン構造
- build（溜め）: 視線・呼吸・空気感の描写
- peak（頂点）: 触覚・嗅覚・聴覚の同時描写
- afterglow（余韻）: 感情の沈降・距離再確認

### 必須テスト要素
- 比喩表現の使用パターン
- 感覚描写の密度
- 心理描写の深さ
- 同意表現の有無
- 伏字/直接表現の境界
- 文字数カウント
- 段落数カウント

## ファイル配置

```
tests/fixtures/erotic_mocks/
├── mock_erotic_pure_love.md      # 純愛・情緒重視
├── mock_erotic_taboo.md          # 背徳・心理葛藤
└── mock_erotic_extreme.md        # 過激・感覚変容
```

## テストケースへの組み込み

### 1. テキスト解析テスト
```python
def test_mock_pure_love_has_build_peak_afterglow():
    text = load_mock("mock_erotic_pure_love.md")
    assert has_phase(text, "build")
    assert has_phase(text, "peak")
    assert has_phase(text, "afterglow")
```

### 2. ボキャブラリ適合テスト
```python
def test_mock_extreme_uses_intense_vocabulary():
    text = load_mock("mock_erotic_extreme.md")
    vocab = get_vocabulary_for_tier("intense")
    matches = count_vocabulary_matches(text, vocab)
    assert matches >= 10  # intense tier は十分な語彙を使用
```

### 3. メタファーフィルタテスト
```python
def test_mock_taboo_passes_metaphor_filter():
    text = load_mock("mock_erotic_taboo.md")
    filtered = metaphor_filter(text, intensity=4)
    assert_no_direct_expressions(filtered)
```

### 4. 強度スケーリングテスト
```python
def test_mock_intensity_scaling():
    mocks = [
        ("mock_erotic_pure_love.md", 3),
        ("mock_erotic_taboo.md", 4),
        ("mock_erotic_extreme.md", 5),
    ]
    for mock_name, expected_intensity in mocks:
        text = load_mock(mock_name)
        score = estimate_intensity_from_text(text)
        assert score == expected_intensity
```

## 実装手順

1. 各モックファイルのMarkdown作成
2. テストヘルパー関数の追加 (`tests/fixtures/erotic_mocks/__init__.py`)
3. テストケースの作成 (`tests/test_erotic_mocks.py`)
4. 既存テストのリファクタリング（モックを使用するように変更）

## 注意事項

- モックテキストは実際の小説スタイルで記述
- 各強度の特徴が明確に表れるように記述
- テストしやすいようにセクション区切りを明記
- 著作権に抵触しないオリジナルテキスト