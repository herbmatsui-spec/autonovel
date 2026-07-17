# ADR-0005: DI Container Consolidation

**Date:** 2026-07-17
**Status:** Proposed
**Decider(s):** Kilo (Software Engineer)

## 1. Context

`config/container.py:Container` と `src/core/container.py:AppContainer` の2つの `DeclarativeContainer` が併存している。役割分担が曖昧で、以下の問題がある。

- `Container.db()` を `AppContainer` に手動で注入するコードが複数箇所に重複
- `db`, `vector_store`, `config`, `global_config` が二重定義
- `Provide["config.container.AppContainer.uow"]` のような文字列参照が混在し、静的解析が効かない
- wiring 対象が重複し、どちらが何を担うか不明確
- 新規プロバイダ追加時の配置先判断が毎回曖昧

## 2. Decision

`InfraContainer` + `AppContainer` の2層構造に統一し、`config/container.py` は薄い互換ラッパに移行する。

## 3. Considered Options

- **Option A: Single Container** — 1つに統合。シンプルだが責務が混在。
- **Option B: Hierarchical (InfraContainer + AppContainer)** — 推奨。責務が明確で拡張性が高い。
- **Option C: Multiple isolated containers** — 複雑化のリスク。

## 4. Decision Outcome

**Chosen Option: Option B (Hierarchical)**

## 5. Implementation Plan

Phase A: 準備 (steps 1-10)
Phase B: 階層化基盤 (steps 11-30)
Phase C: 文字列参照→シンボル参照 (steps 31-40)
Phase D: provider 文字列import→type import (steps 41-55)
Phase E: `Container()` 新規生成禁止 (steps 56-70)
Phase F: `make_container(api_key)` 導入 (steps 71-85)
Phase G: 本格階層化移行 (steps 86-120)
Phase H: Override TestContainer (steps 121-140)
Phase I: Profiles/Lifecycle (steps 141-160)
Phase J: 旧 Container 廃止 (steps 161-180)
Phase K: ADR/規約完成 (steps 181-200)

## 6. Consequences

- 既存コードの `from config.container import Container` は `from src.core.container import InfraContainer` に移行
- `Container()` 直接生成は `get_container()` または `make_container()` に移行
- 新規コンテナ作成は禁止
