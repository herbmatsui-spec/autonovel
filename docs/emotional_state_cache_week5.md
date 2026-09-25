# 感情状態キャッシュ Week 5 - 階層的エージェントメモリ 運用ガイド

## 1. 概要
Week 5 では、MemGPT流の自律管理パラダイムに基づき、執筆エージェントに **3層階層メモリ（Core / Working / Archival）** を実装しました。
エージェントは自律的にツール（Function Calling）を呼び出して感情状態を更新し、トークン上限に応じて古い情報を外部長期記憶へ圧縮・退避します。

## 2. 3層メモリアーキテクチャ
```
┌─────────────────────────────────────────────────────────────┐
│                       WriterAgent                           │
│                                                             │
│   ┌─────────────────┐   ┌─────────────────┐                 │
│   │   CoreMemory    │   │  WorkingMemory  │ (直近シーン揮発) │
│   │   (常駐・JSON)   │   │  (Frame Stack)  │                 │
│   └────────┬────────┘   └────────┬────────┘                 │
│            │ (圧縮・退避)         │ (溢れ時退避)             │
│            └───────────┬─────────┘                          │
│                        ▼                                    │
│             ┌─────────────────────┐                         │
│             │   ArchivalMemory    │ (長期記憶・検索)          │
│             │  (Vector/Log/Graph) │                         │
│             └─────────────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

- **CoreMemory (常駐)**: 現在のキャラクター感情、関係性軌跡、アクティブな対立フックを保持。プロンプトに直接注入される。
- **WorkingMemory (揮発)**: シーン単位のフレームスタック。3〜5フレームを超えると最古フレームが自動的に Archival へ退避。
- **ArchivalMemory (長期)**: 過去全エピソードの感情要約・詳細シーン・因果関係を蓄積し、類似検索や因果追跡を提供。

## 3. 提供ツール群
1. `update_emotion(source, target, emotion, delta, reason)`: 感情値のデルタ加算更新
2. `get_emotional_context(source, target)`: ペアの感情状態照会
3. `recall_similar_scene(query, k)`: 過去類似シーンの想起
4. `trace_emotional_cause(source, target, emotion)`: 感情の因果関係追跡
5. `add_relationship_note(pair, note)`: 関係性メモ記録
6. `compact_core_memory()`: トークン圧縮実行
7. `set_active_hook(hook)`: 今話対立フック設定
