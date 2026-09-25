# 感情残基抽出パイプライン Week 1 - 動作確認ガイド

## 概要
エピソード終了時にルールベースで感情ベクトルを抽出し、Redis Vectorストアに保存。
次話執筆プロンプト冒頭に「直前話からの引き継ぎ感情」として自動注入する機能。

## 依存関係インストール

```bash
# 必須
pip install spacy redis fakeredis pyyaml jinja2

# 日本語NLP (GiNZA) - 推奨
pip install ja-ginza

# テスト用
pip install pytest pytest-asyncio fakeredis

# 開発用
pip install ruff mypy
```

## 設定ファイル配置場所

| ファイル | 用途 |
|---------|------|
| `config/emotion_lexicon.yaml` | 感情語彙辞書・依存構造パターン |
| `config/characters.yaml` | 登場キャラクター名リスト |
| `config/context_compression.yaml` | 圧縮パイプライン設定（感情残基セクション含む） |
| `config/redis.yaml` | Redis接続設定 |
| `templates/emotional_context.j2` | 感情ベクトル自然言語化テンプレート |
| `prompts/templates/narrative/final_writing_prompt.j2` | 執筆プロンプト（注入ポイント含む） |

## 手動実行コマンド例

### 1. 感情残基抽出器の単体テスト
```bash
cd E:\hhh
python -m pytest tests/unit/pipeline/test_emotional_residue.py -v
python -m pytest tests/unit/pipeline/test_signal_extractor.py -v
python -m pytest tests/unit/pipeline/test_aggregator.py -v
```

### 2. パイプライン統合テスト
```bash
python -m pytest tests/integration/pipeline/test_emotional_residue_e2e.py -v
```

### 3. プロンプト注入テスト
```bash
python -m pytest tests/unit/templates/test_final_writing_prompt.py -v
python -m pytest tests/integration/agent/test_writer_prompt_injection.py -v
```

### 4. リグレッションテスト全実行
```bash
python -m pytest tests/regression/test_emotional_residue_regression.py -v
```

### 5. 全テスト実行
```bash
python -m pytest tests/unit/pipeline/ tests/unit/config/ tests/unit/stores/ tests/unit/templates/ tests/integration/pipeline/ tests/integration/agent/ tests/regression/test_emotional_residue_regression.py -v
```

## 期待される出力例

### 感情ベクトル抽出結果（ログ）
```
INFO:Ep.14: 感情残基抽出完了
```

### 生成されるプロンプト冒頭（final_writing_prompt.j2）
```
本文開始前に [thought_process] を出力せよ:
1. シーンごとの緩急の峻別 2. 目標文字数配分 3. 読者の情緒を破壊する一文 4. 五感情報の優先順位 5. 冒頭・末尾のフック戦略

【直前話からの引き継ぎ感情】
A→B: affection(0.3)、fear(0.8) (主要: fear(0.8)) [原因: ep14_betrayal]
B→A: sadness(0.6) (主要: sadness(0.6))

{{ quota_inst }}
...
```

### Redis保存キー例
```
emotional:pipeline:ep14:A->B
emotional:pipeline:ep14:B->A
emotional:pipeline:ep15:A->B
...
```

## よくあるエラーと対処

### 1. `ja_ginza` モデルが見つからない
```
OSError: [E050] Can't find model 'ja_ginza'
```
**対処**: `pip install ja-ginza` を実行、または `python -m spacy download ja_ginza`

### 2. Redis接続エラー
```
redis.exceptions.ConnectionError: Error 10061 connecting to localhost:6379
```
**対処**: 
- Redisサーバーが起動しているか確認 (`redis-cli ping`)
- テスト時は `skip_connection_check=True` または `fakeredis` 使用
- `.env` に `REDIS_URL` 設定

### 3. `sentencizer` コンポーネント未追加
```
ValueError: [E030] Sentence boundaries unset.
```
**対処**: `nlp.add_pipe("sentencizer")` を実行（テストフィクスチャで自動追加済み）

### 4. テンプレートシンタックスエラー
```
jinja2.exceptions.TemplateSyntaxError: expected token 'end of statement block'
```
**対処**: `templates/emotional_context.j2` の Jinja2 文法を確認

### 5. 感情コンテキストがプロンプトに出力されない
**確認事項**:
- `prompts/manager.py` で `EMOTIONAL_RESIDUE_AVAILABLE` が `True` か
- `build_emotional_context_prompt` が正しく呼ばれているか
- `final_writing_prompt.j2` に `{% if emotional_context %}` ブロックがあるか
- Redis に前話のベクトルが保存されているか (`ep{num}:{source}->{target}`)

### 6. ベクトルが保存されない
**確認事項**:
- `EpisodeWriter` に `vector_store` が注入されているか
- `_get_emotional_extractor()` が呼ばれているか
- `extractor.extract_and_persist()` で例外が発生していないか（ログ確認）

## アーキテクチャ概要

```
EpisodeWriter.write() 
    → EpisodeWriter.run() 
        → emotional_extractor.extract_and_persist(ep_num, written_text)
            → NLP処理 (GiNZA)
            → キャラ抽出
            → 依存構造ベース感情シグナル抽出
            → 集約 (EmotionalVector)
            → RedisVectorStore.upsert("pipeline", key, vector)
    
次話執筆時:
PromptManager.build_final_writing_prompt()
    → build_emotional_context_prompt(ep_num, vector_store)
        → vector_store.get_latest("pipeline", pair)
        → emotional_context.j2 レンダリング
    → final_writing_prompt.j2 に注入
```

## カスタマイズポイント

### 感情語彙追加
`config/emotion_lexicon.yaml` の `emotion_lexicon.<感情タイプ>.positive/negative` に追加

### 依存構造パターン追加
`config/emotion_lexicon.yaml` の `dependency_patterns` に `[主語dep, 目的語dep, 感情タイプ, 重み]` 形式で追加

### TTL変更
`config/redis.yaml` の `namespace_ttls` でネームスペース別設定

### プロンプト表示形式変更
`templates/emotional_context.j2` を編集

## トラブルシューティングフローチャート

```
感情が注入されない
    │
    ├─ Redisにキーがあるか？ → ない → EpisodeWriterで抽出エラー → ログ確認
    │                           ある → 次へ
    │
    ├─ build_emotional_context_prompt が呼ばれるか？ → 呼ばれない → PromptManager確認
    │                                                    呼ばれる → 次へ
    │
    ├─ vector_store.get_latest が値を返すか？ → 返さない → キー形式確認 (ep{num}:{src}->{tgt})
    │                                          返す → 次へ
    │
    └─ テンプレートレンダリング結果に感情文言があるか？ → ない → emotional_context.j2確認
                                                             ある → final_writing_prompt.j2確認
```

## パフォーマンス目安

| 処理 | 目安時間 |
|------|---------|
| NLP処理 (1話分 ~5000文字) | 100-500ms |
| 感情抽出・集約 | 10-50ms |
| Redis保存 | 1-5ms |
| プロンプト生成 (次話) | 5-20ms |

## 次のステップ (Week 2以降)

- Week 2: ルールエンジン・プロット連動ベースライン生成
- Week 3: 構造化アノテーション・エディタ統合
- Week 4: 融合レイヤー・矛盾検出
- Week 5: 階層的エージェントメモリ