# AutoNovel (オートノベル)

<div align="center">

**次世代AI小説執筆・マルチエージェント・GraphRAG・納品オーケストレーション基盤**

*FastAPI + React 18/TypeScript + Huey Task Queue + SQLAlchemy 2.0 + GraphRAG (Apache AGE + pgvector) + PostgreSQL 16 / Redis 7 / ChromaDB*

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/react-18.3-61dafb?logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Apache AGE](https://img.shields.io/badge/Graph-Apache_AGE-D22128)](https://age.apache.org/)
[![ChromaDB](https://img.shields.io/badge/Vector-ChromaDB-FF6F61)](https://www.trychroma.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue)](https://mypy-lang.org/)
[![Vitest](https://img.shields.io/badge/tested_with-vitest-729B1B?logo=vitest&logoColor=white)](https://vitest.dev/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

<br />

<p align="center">
  <img src="docs/demo.gif" alt="AutoNovel UI & Workflow Demo" width="900" style="border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
</p>

*▲ AutoNovel v4.0: 3案企画ガチャ / 逆算プロット / 上級者Studio / インライン五感推敲 / GraphRAG相関図 / ワンクリックZIP納品 / マルチメディア・eBook / IF分岐・共同編集 (CRDT)*

</div>

---
## 何ができるの？（初心者向け概要）

AutoNovel は、AI を活用して Web 小説を **企画から執筆、校正、挿絵生成、納品まで** をワンストップで行えるツールです。プログラミングや AI の専門知識がなくても、ブラウザ上の簡単なフォームに情報を入力するだけで、数十秒で第1話が生成され、ZIP ファイルとしてダウンロードできます。

### 主な特徴

- **かんたんモード**：ジャンル・主人公設定だけで数十秒で第1話を生成
- **ワンクリック納品**：本文・設定・プロット・データを 1 つの ZIP にまとめて出力
- **AI 挿絵自動生成**：重要シーンのイラストを自動で作成
- **マルチメディア生成**：シーン画像・立ち絵・表紙・ボイス・BGM などのアセットパックを生成
- **eBook エクスポート**：縦書き・EPUB 3 準拠の電子書籍ファイルを直接出力
- **マルチモード**：初心者向け Easy Mode と、プロ向け Advanced Mode / 上級者 Studio を切り替えて利用可能
- **共同編集 (CRDT)**：複数執筆者による `ChapterVersion` のベクタークロック同期マージ

### まずは試してみよう

1. リポジトリをクローンし、`アプリ起動.bat`（Windows）または `docker compose up`（Docker）を実行
2. ブラウザで `http://localhost:5173` を開く
3. 「かんたん執筆」タブでジャンル・主人公・冒頭を入力し、**開始** をクリック
4. 生成された本文を確認し、**ZIP ダウンロード** ボタンで納品パッケージを取得

続いて、下記の目次から技術的な詳細をご覧ください。


## 📖 目次

- [1. AutoNovel プロジェクト概要](#1-autonovel-プロジェクト概要)
  - [1.1 プロジェクトの背景とビジョン](#11-プロジェクトの背景とビジョン)
  - [1.2 解決するWeb小説AI制作の課題](#12-解決するweb小説ai制作の課題)
  - [1.3 コア設計原則](#13-コア設計原則)
- [2. 主要機能一覧 & 2大制作モード](#2-主要機能一覧--2大制作モード)
  - [2.1 制作モード比較](#21-制作モード比較)
  - [2.2 かんたん制作モード (Easy Mode)](#22-かんたん制作モード-easy-mode)
  - [2.3 上級者 Studio (Sudowrite × Notion AI 式 統合エディタ)](#23-上級者-studio-sudowrite--notion-ai-式-統合エディタ)
  - [2.4 GraphRAG & 長期記憶ナレッジグラフ](#24-graphrag--長期記憶ナレッジグラフ)
  - [2.5 多角型品質監査 & 読者フック診断システム](#25-多角型品質監査--読者フック診断システム)
  - [2.6 AI挿絵プロンプト & ビジュアル生成エンジン](#26-ai挿絵プロンプト--ビジュアル生成エンジン)
  - [2.7 自動マーケティング & 納品パッケージング](#27-自動マーケティング--納品パッケージング)
    - [2.7.1 マルチメディア生成 (`multimedia` router)](#271-マルチメディア生成-multimedia-router)
    - [2.7.2 共同編集とCRDT (`collab` router)](#272-共同編集とcrdt-collab-router)
    - [2.7.3 IFルート分岐](#273-ifルート分岐)
- [3. システムアーキテクチャ & 技術スタック](#3-システムアーキテクチャ--技術スタック)
  - [3.1 全体アーキテクチャ図](#31-全体アーキテクチャ図)
  - [3.2 採用技術スタック一覧](#32-採用技術スタック一覧)
  - [3.3 フロントエンド構成](#33-フロントエンド構成)
  - [3.4 バックエンド API 構成](#34-バックエンド-api-構成)
  - [3.5 非同期タスク実行基盤](#35-非同期タスク実行基盤)
  - [3.6 知識・永続化層](#36-知識永続化層)
- [4. マルチエージェント・オーケストレーション詳細](#4-マルチエージェントオーケストレーション詳細)
  - [4.1 エージェント群の責務分担](#41-エージェント群の責務分担)
  - [4.2 専門エージェント詳細](#42-専門エージェント詳細)
  - [4.3 マルチエージェント協調シーケンス](#43-マルチエージェント協調シーケンス)
- [5. GraphRAG & 長期記憶・コンテキストマネジメント](#5-graphrag--長期記憶コンテキストマネジメント)
  - [5.1 動的世界観Bible管理とエンティティ抽出](#51-動的世界観bible管理とエンティティ抽出)
  - [5.2 ナレッジグラフとベクトルストアのハイブリッド検索](#52-ナレッジグラフとベクトルストアのハイブリッド検索)
  - [5.3 コンテキストウィンドウ管理 & セマンティックキャッシュ](#53-コンテキストウィンドウ管理--セマンティックキャッシュ)
- [6. 非同期パイプライン & ライフサイクル管理](#6-非同期パイプライン--ライフサイクル管理)
  - [6.1 タスクステートマシン](#61-タスクステートマシン)
  - [6.2 非同期生成・ステータスポーリングシーケンス](#62-非同期生成ステータスポーリングシーケンス)
  - [6.3 トランザクション保護とフォールバック保証](#63-トランザクション保護とフォールバック保証)
- [7. データモデル & ER設計](#7-データモデル--er設計)
  - [7.1 ドメインモデル ER図](#71-ドメインモデル-er図)
  - [7.2 主要エンティティ仕様](#72-主要エンティティ仕様)
- [8. ディレクトリ構成 & コードベースマップ](#8-ディレクトリ構成--コードベースマップ)
  - [8.1 全体ディレクトリツリー](#81-全体ディレクトリツリー)
  - [8.2 レイヤー責務と境界設計](#82-レイヤー責務と境界設計)
- [9. 必要動作環境](#9-必要動作環境)
- [10. クイックスタート & 起動ガイド](#10-クイックスタート--起動ガイド)
  - [10.1 Windows ワンクリック起動](#101-windows-ワンクリック起動)
  - [10.2 Docker Compose による起動](#102-docker-compose-による起動)
  - [10.3 ローカル手動環境構築](#103-ローカル手動環境構築)
- [11. 実践操作マニュアル & 納品パッケージ仕様](#11-実践操作マニュアル--納品パッケージ仕様)
  - [11.1 かんたんモード操作ステップ](#111-かんたんモード操作ステップ)
  - [11.2 3案企画ガチャと上級者モード昇格](#112-3案企画ガチャと上級者モード昇格)
  - [11.3 ナレッジグラフ可視化ツールの活用](#113-ナレッジグラフ可視化ツールの活用)
  - [11.4 納品パッケージ (ZIP) の構造とフォーマット仕様](#114-納品パッケージ-zip-の構造とフォーマット仕様)
- [11.5 商用出版API連携 (なろう/カクヨム/Kobo/Kindle)](#115-商用出版api連携-なろうカクヨムkobokindle)
- [12. LLMプロバイダ設定 & ルーティング・拡張ガイド](#12-llmプロバイダ設定--ルーティング拡張ガイド)
  - [12.1 サポートプロバイダと切り替え設定](#121-サポートプロバイダと切り替え設定)
  - [12.2 プロバイダファクトリとアダプタアーキテクチャ](#122-プロバイダファクトリとアダプタアーキテクチャ)
  - [12.3 カスタムLLMアダプタの実装例](#123-カスタムllmアダプタの実装例)
- [13. REST API 完全リファレンス](#13-rest-api-完全リファレンス)
  - [13.1 主要エンドポイント一覧](#131-主要エンドポイント一覧)
  - [13.2 かんたんモード系 API](#132-かんたんモード系-api)
  - [13.3 ナレッジグラフ・挿絵・マーケティング系 API](#133-ナレッジグラフ挿絵マーケティング系-api)
  - [13.4 オブザーバビリティ系 API](#134-オブザーバビリティ系-api)
- [14. 設定パラメータ & 環境変数リファレンス](#14-設定パラメータ--環境変数リファレンス)
- [15. セキュリティ & 堅牢性設計](#15-セキュリティ--堅牢性設計)
- [16. オブザーバビリティ (ロギング・ヘルス・メトリクス)](#16-オブザーバビリティ-ロギングヘルスメトリクス)
- [17. 本番デプロイ & インフラ運用設計](#17-本番デプロイ--インフラ運用設計)
- [18. テスト戦略 & 品質ゲート](#18-テスト戦略--品質ゲート)
- [19. トラブルシューティング & FAQ](#19-トラブルシューティング--faq)
- [20. 開発ワークフロー & コントリビューション](#20-開発ワークフロー--コントリビューション)
- [21. ロードマップ & ライセンス](#21-ロードマップ--ライセンス)

---

## 1. AutoNovel プロジェクト概要

### 1.1 プロジェクトの背景とビジョン

**AutoNovel** は、Web小説（ハイファンタジー、ダークファンタジー、異世界転生、現代ダンジョン、R15作品群など）の企画・世界観構築・プロット策定・マルチブランチ執筆・品質監査・挿絵生成・データ納品までを自律的かつ高度に協調して遂行する**次世代AI小説制作オーケストレーション基盤**です。

単なるチャット型プロンプト入力による短文生成ツールとは異なり、AutoNovel は数十万字規模の長編連載小説を商業・Web投稿レベルで一貫性を保ちながら完結させるためのエンタープライズ・アーキテクチャを備えています。

```
+-----------------------------------------------------------------------------------+
|                                   AutoNovel Core                                  |
|                                                                                   |
|  [企画・プロット] ──> [世界観Bible/GraphRAG] ──> [本文執筆] ──> [品質監査/診断]   |
|         │                        │                     │               │          |
|         ▼                        ▼                     ▼               ▼          |
|    PlanningAgent            BibleAgent           WritingAgent      AuditAgent     |
|   (3案企画ガチャ)        (知識グラフ/ベクトル)    (コンテキスト構築)  (カタルシス/伏線)  |
|                                                                        │          |
|                                                                        ▼          |
|  [納品パッケージZIP] <── [挿絵生成] <── [マーケティング/あらすじ] <───────┘          |
|    (01_本文.txt / 02_設定集.txt / 03_プロット.txt / 04_データダンプ.json)         |
+-----------------------------------------------------------------------------------+
```

### 1.2 解決するWeb小説AI制作の課題

近年の大規模言語モデル（LLM）の進化によりテキスト生成は容易になりましたが、本格的な長編小説制作では以下の5つの重大な技術的・構造的障壁が存在していました：

1. **文脈喪失と設定の矛盾 (Context Drift & Hallucination)**:
   - 従来手法: 話数が進むにつれて過去の設定やキャラクターの口調、死亡した登場人物の扱い、スキル制約が忘れられ、矛盾が多発する。
   - AutoNovelの解決策: **世界観Bible (設定辞書)** と **GraphRAG (Apache AGE ナレッジグラフ + VectorStore)** により、登場人物の関係性や世界観ルールをグラフ構造として恒久管理し、執筆時に動的注入。
2. **Webサーバーのタイムアウトと生成中断 (Timeout & State Loss)**:
   - 従来手法: 同期HTTPリクエストで長文生成を行うと、LLMの推論遅延によりHTTPタイムアウトや通信切断が発生し、途中結果が喪失する。
   - AutoNovelの解決策: **Huey Task Queue + Redis/SQLite** による完全非同期キューイングとステートマシン管理を採用。生成タスクはバックグラウンドワーカーで実行され、クライアントはポーリングやSSEで安全に進捗を受け取る。
3. **構成の平坦化とカタルシス不足 (Flat Narrative & Pacing Issues)**:
   - 従来手法: AIは無難な展開を好むため、起承転結の「転」や読者の感情を揺さぶる「カタルシス」「テンション曲線」「引き（フック）」が欠落しやすい。
   - AutoNovelの解決策: **テンション曲線設計 (Tension Curve Engine)** と **カタルシス種別管理 (Catharsis Scoring)**、および **読者フック診断 (HookDiagnoser)** による構造的プロット制御。
4. **挿絵・プロモーション・納品の一連の断絶 (Disjointed Deliverables)**:
   - 従来手法: 生成された文章をコピペし、別ツールで画像生成し、手作業で設定資料やあらすじをまとめる膨大な事務作業が発生する。
   - AutoNovelの解決策: **MarketingAgent** と **IllustrationAgent** が連動し、本文・設定集・プロット概要・JSONダンプ・挿絵プロンプトを一括でZIPアーカイブにパッケージングしてワンクリック納品。
5. **プロバイダ依存とコスト管理 (Vendor Lock-in & Token Explosion)**:
   - 従来手法: 特定のLLM APIに密結合し、API利用料の急騰やサービス停止に脆弱。
   - AutoNovelの解決策: **LLM Gateway / Provider Factory** による疎結合化（OpenAI, Gemini, Mock実装済み / Claude, Ollama, vLLM は OpenAI 互換モードで利用可能）、プロンプトキャッシング、セマンティックキャッシュ、トークン・コスト追跡を完備。

### 1.3 コア設計原則

- **Clean Architecture & Domain-Driven Design**:
  ビジネスロジック（小説制作ドメイン）、データ永続化（リポジトリ層）、非同期タスク、APIインターフェースを明確に分離。
- **Resilience First (回復性最優先)**:
  LLM APIの一時的な障害やレート制限に対して、指数バックオフ付き自動リトライ、フォールバック機構、サーキットブレーカーを適用。
- **Multi-Modal Extensibility (マルチモーダル拡張性)**:
  テキスト執筆のみならず、キャラクター立ち絵・挿絵生成プロンプトの自動設計や音声化への拡張性を見据えたモジュラー設計。
- **Zero-Config Developer Experience (ゼロコンフィグ開発体験)**:
  Windowsバッチ、Docker Compose、ローカルSQLite環境など、あらゆる環境でコマンド1つまたはダブルクリックのみで即座に起動可能。

---

## 2. 主要機能一覧 & 2大制作モード

### 2.1 制作モード比較

AutoNovel は、目的と制作深度に合わせて**2つの強力な制作モード**を提供します：

| 比較項目 | かんたん制作モード (Easy Mode) | アドバンスド・パイプライン (Advanced Mode) |
| :--- | :--- | :--- |
| **対象ユーザー** | 初心者、アイデア検証、即座の執筆・納品 | プロ作家、本格長編連載、厳密な世界観管理 |
| **入力パラメータ** | ジャンル、主人公設定（名前・性格・能力）、冒頭文 | 企画コンセプト、章別プロットツリー、登場人物相関、世界観ルール |
| **生成単位** | 1話ごとの連続生成 & サジェスチョン | 全体構成 → 章プロット → シーン設計 → 本文執筆 → 品質監査 |
| **設定管理** | インテリジェント・ダイジェスト自動抽出 | 世界観Bible + GraphRAG + 伏線追跡テーブル |
| **分岐管理** | リニア進行（ワンクリック昇格対応） | マルチブランチ (Git like なルート分岐・リビルド) |
| **所要時間** | 数十秒で即座に第1話完成・ZIP出力 | 数分〜数十分で複数章の総合オーケストレーション |
| **昇格パス** | ボタン1つでアドバンスド作品へ完全コンバート | 随時、詳細設定の追加・微調整が可能 |

---

### 2.2 かんたん制作モード (Easy Mode)

Web UI からわずか数項目のフォームを入力するだけで、プロ品質の小説第1話を生成し、連続して次話の執筆を行える直感的なモードです。

```
[3案企画ガチャ / 逆算プロット] ──> [主人公 & 冒頭設定] ──> [AIかんたん執筆] ──> [リアルタイム進捗]
                                                                                      │
[ワンクリック納品ZIP] <── [上級者Studioへ昇格] <── [次話サジェスト / 本文エディタ] <──────┘
```

- **🎲 3案企画ガチャ (Gacha Pitch - `POST /api/easy-mode/gacha`)**:
  漠然としたキーワードやジャンルから、AIが方向性の異なる3案（⚔️王道、🌀変化球、🌑ダーク）の企画・タイトル・ログライン・主人公設定を即座に同時提案。
- **🔮 逆算プロットビルダー (4-Step Reverse Engineering - `POST /easy_mode/reverse-generate`)**:
  「最終話で読者に残したい感情」「主人公が支払う代償」「核心の衝突」「第1話の開幕フック」の4ステップを選択するだけで、全10話・3アーク構成とカタルシス波形を同期型で瞬時に算出・第1話プロンプトへ自動展開。
- **📝 インテリジェント・ダイジェスト生成 (`POST /api/easy-mode/digest`)**:
  企画ガチャの選択案から、詳細なあらすじ・第1話草案・クライマックス予告テキストを自動創出。
- **📦 最新本文連動 ZIP エクスポート (`POST /easy_mode/export-with-data`)**:
  画面上でユーザーが推敲・手動編集した最新の本文テキスト・キャラクター設定を完全同期し、瞬時に納品用ZIP（本文、設定集、プロット、JSONダンプ）として出力。
- **🚀 上級者 Studio へワンクリック昇格 (`POST /api/easy-mode/promote`)**:
  かんたんモードで作成した設定・本文をGraphRAGナレッジグラフに自動登録し、Sudowrite × Notion AI 式の高度なエディタワークスペースへシームレスに移行。
- **🎬 マルチメディアアセットパック生成 (`POST /multimedia/generate`)**:
  `ENABLE_MULTIMEDIA` 有効時、シーン画像 / キャラクター立ち絵 / 表紙 / ボイス / BGM を一括ビルドし、ZIP 納品物へ同梱。
- **📕 eBook エクスポート (`POST /export/ebook`)**:
  縦書き・ルビ・目次・本文 XHTML を内包した EPUB 3 ファイルを即座に出力。`POST /easy_mode/export-with-data` でも同梱可能。

---

### 2.3 上級者 Studio (Sudowrite × Notion AI 式 統合エディタ)

長編Web小説のプロ作家・ディレクター向けの本格制作統合スタジオです。

- **3カラム統合ワークスペース (`src/components/studio/StudioWorkspace.tsx`)**:
  - **左ペイン**: 主人公設定・世界観パラメータ・ジャンル設定のリアルタイム同期。
  - **中央ペイン**: ルビ記法（`｜親文字《ルビ》`）プレビュー対応リッチエディタ & 次の展開提案。
  - **右ペイン**: GraphRAG 専属 AI 編集者（設定Q&A & リアルタイム矛盾診断）。
- **章構成ツリービュー (`src/components/studio/ChapterOutlineTree.tsx`)**:
  作品全体の章・プロット構造をツリー形式で表示・編集。
- **🪄 インライン五感推敲ツールバー (`src/components/editor/InlineAiToolbar.tsx`)**:
  本文中の任意のテキストを選択するとフローティングツールバーが出現。
  - **五感描写**: 👁️視覚（光影や細部）、👂聴覚（環境音・声）、👃嗅覚（大気の匂い）、✋触覚（肌触り・温度）、✨比喩（詩的表現）
  - **🎭 Show, Don't Tell**: 感情の説明を行動・情景描写へと自動昇華
  - **トーン変換**: ⚡緊迫感UP、⏩テンポ加速
  - **テキスト保護**: 提案プレビュー確認後、選択範囲のみの「置換」または「直後追記」を安全に実行。
- **🔮 Next Beats (次の展開 3案生成 - `src/components/editor/NextBeatsPanel.tsx`)**:
  現在の執筆文脈・ジャンルから、物語を加速させる3つの分岐展開（必殺の一撃、仲間の救援、衝撃の真実など）を緊張度スコア付きで提案。
- **🧠 専属 AI 編集者 (Ask Bible & リアルタイム矛盾チェック - `src/components/editor/EditorialSidebar.tsx`)**:
  - **Ask Bible**: 「古代魔導剣の弱点は？」などの疑問にGraphRAGナレッジから根拠（出典）付きで即答。
  - **矛盾診断**: 本文のキャラクター行動や世界観設定を自動照合し、設定ブレやタイムラインの破綻を検知。
- **📦 アセットパックパネル (`src/components/AssetPackPanel.tsx`)**:
  マルチメディア（シーン画像・立ち絵・表紙・ボイス・BGM）の生成進捗管理とZIPダウンロード。

---

### 2.4 GraphRAG & 長期記憶ナレッジグラフ

長編執筆における「設定の矛盾」を技術的に根絶するハイブリッド記憶システムです。

- **Apache AGE 連携ナレッジグラフ (`graph_pipeline.py`, `age_client.py`)**:
  キャラクター間の人間関係（友好、敵対、師弟、片思いなど）やアイテム・所属組織の関係をグラフデータベース上で追跡。
- **VectorStore & セマンティック検索 (`vector_store.py`, `rag_service.py`)**:
  過去エピソードや世界観設定のテキスト埋め込み（Embedding）を保持し、現在のシーンに関連する設定をミリ秒単位で検索してプロンプトへ注入。
- **インタラクティブ・物理演算グラフ可視化 (`GraphVisualization.tsx`)**:
  Force-Directed 物理シミュレーションにより、キャラクター・場所・アイテム・勢力の相関ネットワークを直感的に探索・ノード詳細表示。

---

### 2.5 多角型品質監査 & 読者フック診断システム

プロ編集者視点の多面的メトリクスにより、生成されたテキストの品質を自動検証・採点します。

- **読者引き込み診断 (`HookDiagnoser`)**:
  エピソード冒頭の「謎・違和感・危機」や、末尾の「クリフハンガー（次話への引き）」の強度をスコアリング。
- **序盤エンタメ度判定 (`EarlyEntertainmentChecker`)**:
  Web小説の第1話〜第3話で読者が離脱しないよう、主人公の魅力提示やストレス展開の早期解消を監査。
- **文体・整合性監査 (`AuditAgent`, `StructureValidator`)**:
  キャラクターの口調ブレ、不自然な敬語、世界観ルール違反、誤字脱字を検知し、修正パッチ（`Patch`）を自動生成。

---

### 2.6 AI挿絵プロンプト & ビジュアル生成エンジン

小説内の名シーンを自動検出し、高品質な画像生成プロンプト（Midjourney, Stable Diffusion, DALL-E 3, Imagen 向け）を自動生成・画像化します。

- **シーン抽出 (`IllustrationAgent`)**:
  エピソード中のクライマックス、キャラクター登場シーン、戦闘シーンをAIが自動選定。
- **キャラクターデザイン一貫性維持**:
  世界観Bibleに登録されたキャラクターの髪型・瞳の色・服装・装飾品の設定を自動反映し、話数が進んでもキャラクターの外見的一貫性を維持。

---

### 2.7 自動マーケティング & 納品パッケージング

執筆完了後の作品を、Web小説投稿サイト（小説家になろう、カクヨム、アルファポリス等）や電子書籍納品用フォーマットへ自動変換します。

- **マーケティング支援 (`MarketingAgent`, `PromotionService`)**:
  作品タイトル案（トレンドキーワード入り）、キャッチコピー（10文字〜30文字）、あらすじ（300文字版 / 800文字版）、おすすめタグ一覧を自動生成。
- **ワンクリック ZIP パッケージ出力 (`POST /easy_mode/export-with-data` & `GET /easy_mode/export/{book_id}`)**:
  本文、設定集、プロット概要、JSONダンプを整理されたディレクトリ構造でZIP化し、即座にダウンロード可能。

#### 2.7.1 マルチメディア生成 (`multimedia` router)
`ENABLE_MULTIMEDIA=true` で有効化。以下のエンドポイントで各種アセットを生成・管理します：

- **統合アセットパック生成**: `POST /multimedia/generate` (README互換エイリアス) / `POST /multimedia/asset-pack` - IFルート、メディアミックス台本、eBook を含む統合ZIPを生成
- **メディアミックス台本生成**: `POST /multimedia/media-mix` - `manga` / `audio_drama` / `video` / `light_novel` / `webtoon` 形式の台本を生成
- **IFルートグラフ生成**: `POST /multimedia/if-routes` - 分岐プロットグラフを生成・永続化
- **eBook エクスポート**: `POST /multimedia/ebook` (または `POST /api/export/ebook`) - EPUB 3 / PDF / MOBI 形式で出力
- **タスク進捗確認**: `GET /multimedia/tasks/{task_id}` - 非同期生成タスクのステータス取得
- **アセット一覧取得**: `GET /multimedia/assets/{book_id}` - 指定作品の全アセットメタデータを取得
- **ファイルダウンロード**: `GET /multimedia/artifacts/{asset_id}/download` - 成果物ファイル本体をダウンロード

アセットパックは納品 ZIP にも同梱されます（[`docs/multimedia.md`](docs/multimedia.md) 参照）。

#### 2.7.2 共同編集とCRDT (`collab` router)
`chapter_versions` テーブルに `vector_clock` (JSON) と `base_version_id` を保持し、複数執筆者による章単位の並行編集を CRDT 的にマージ。`POST /collab/versions` で保存、`GET /collab/versions/{book_id}/{ep}` で履歴・コメントツリーを取得できます。

#### 2.7.3 IFルート分岐
`Branch` モデル + `routers/easy_mode.py` 経由で、main ルートから IF分岐をフォーク・合流可能。各分岐は独立した `plot` ツリー・テンション履歴を持つため、複数エンディングの並列執筆に対応します。


---

## 3. システムアーキテクチャ & 技術スタック

### 3.1 全体アーキテクチャ図

AutoNovel は、モダンなマイクロサービス指向の疎結合レイヤードアーキテクチャを採用しています。

```mermaid
graph TD
    User["クライアント (ブラウザ / Web UI)"]

    subgraph "Frontend Layer (Port 5173 / 8080)"
        UI["React 18 + TypeScript + Vite"]
        GraphVis["GraphVisualization (Force Graph)"]
        Editor["Editor & AI Suggestions"]
        Nginx["Nginx Reverse Proxy (本番時)"]
    end

    subgraph "Backend API Layer (FastAPI, Port 8200)"
        Server["server.py (FastAPI App)"]
        RateLimit["rate_limit.py (Sliding Window Limiter)"]
        EasyRouter["routers/easy_mode.py"]
        GraphRouter["routers/graph.py"]
        BooksRouter["routers/books.py & plots.py"]
        Obs["observability.py (Health & Metrics)"]
        Log["logging_config.py (JSON StructLog)"]
    end

    subgraph "Domain & Persistence Layer"
        Repo["repository.py (BookRepository)"]
        Models["SQLAlchemy 2.0 ORM Models"]
        DB[(PostgreSQL 16 / SQLite WAL)]
        VectorDB[(VectorStore / Embeddings)]
        GraphDB[(Apache AGE Knowledge Graph)]
    end

    subgraph "Async Task Queue Layer"
        HueyBroker["Huey Queue Broker"]
        RedisQueue[(Redis 7 Broker / SQLite)]
        Worker["Huey Consumer (generation_tasks.py)"]
    end

    subgraph "Multi-Agent Orchestration & Services"
        Digest["digest_service.py"]
        GraphPipe["graph_pipeline.py"]
        RAG["rag_service.py & prefetch"]
        Marketing["marketing.py (MarketingAgent)"]
        Audit["audit_service.py (AuditAgent)"]
        LLMFactory["LLM Adapter Factory"]
    end

    subgraph "External AI Providers"
        OpenAI["OpenAI (GPT-4o / o1)"]
        Gemini["Google Gemini (1.5 Pro / Flash)"]
        OpenAICompat["OpenAI-Compatible (Claude/Ollama/vLLM via OpenRouter等)"]
    end

    User -->|HTTP / SPA| Nginx
    Nginx -->|Static Assets| UI
    Nginx -->|Reverse Proxy /easy_mode/*| Server
    UI -->|Direct API (Dev)| Server
    UI --> GraphVis
    UI --> Editor

    Server --> RateLimit
    RateLimit --> EasyRouter
    Server --> GraphRouter
    Server --> BooksRouter
    Server --> Obs
    Server --> Log

    EasyRouter --> Repo
    EasyRouter --> RAG
    BooksRouter --> Repo
    Repo --> Models
    Models --> DB

    EasyRouter -->|Enqueue Task| HueyBroker
    HueyBroker --> RedisQueue
    Worker -->|Dequeue Task| RedisQueue
    Worker --> Digest
    Worker --> GraphPipe
    Worker --> LLMFactory
    Worker --> Marketing
    Worker --> Audit

    GraphPipe --> GraphDB
    RAG --> VectorDB
    RAG --> GraphDB

    LLMFactory --> OpenAI
    LLMFactory --> Gemini
    LLMFactory --> OpenAICompat

    Worker -->|Update Status & Result| Repo
    Worker -->|Increment Metrics| Obs
```

---

### 3.2 採用技術スタック一覧

| レイヤー | 主要技術 | バージョン | 選定理由・役割 |
| :--- | :--- | :--- | :--- |
| **Frontend** | React, TypeScript, Vite | React 18.3, Vite 5.x, TS 5.x | 高速なHMR開発体験、厳格な型安全性、モダンSPA設計 |
| **Styling** | Vanilla CSS (CSS Variables) | Modern CSS3 | 外部CSSフレームワーク依存を排除した軽量・高速・完全カスタマイズ可能なデザインシステム |
| **Graph UI** | `react-force-graph-2d` + SVG | npm `react-force-graph-2d` | キャラクター相関・知識グラフの物理シミュレーション可視化 |
| **Alt UI** | Streamlit | 1.x (`streamlit_app/`) | 設定/ダッシュボード用の軽量代替UI (Settings / Home ページ) |
| **Backend API** | FastAPI, Uvicorn, Pydantic | FastAPI 0.141, Pydantic v2.13 | 高速な非同期I/O、OpenAPI 3.1自動生成、厳格なスキーマ検証 |
| **DI / Container** | dependency-injector | 4.49 | サービス/ルーター/リポジトリのコンテナ化 |
| **Task Queue** | Huey | Huey 3.3 | Celeryより軽量、`redis` / `sqlite` バックエンドのシームレス切替 |
| **Database** | PostgreSQL 16 / SQLite | SQLAlchemy 2.0.52, Alembic 1.13+ | 開発時のゼロコンフィグSQLite(WAL)と本番高負荷PostgreSQLの完全両立 |
| **Graph DB** | Apache AGE (openCypher) | `apache/age-postgresql:16-pgvector` | エンティティ関係性グラフをSQL内で透過的に操作 |
| **Vector Store** | ChromaDB / pgvector / In-Memory | ChromaDB 1.5+, pgvector 0.5 | ベクトル検索バックエンドの選択可（環境変数 `CHROMA_HOST` / `REQUIRE_PG`） |
| **BM25 / Reranker** | rank-bm25 / cross-encoder | extras `rag` | ハイブリッド検索の語彙一致・再ランキング |
| **Caching** | Redis 7 / In-Memory | redis-py 8.x | 分散タスクキュー、レート制限、セマンティックプロンプトキャッシュ |
| **Observability** | OpenTelemetry, Prometheus, python-json-logger | OTel 1.44, prom-client 0.26 | 構造化JSONログ、統合ヘルスチェック、メトリクス収集 |
| **Testing** | pytest, Vitest, RTL, MSW | pytest 8.x, Vitest 1.6 | バックエンド/フロントエンド双方の網羅的単体・統合・モックテスト（カバレッジ 80% ゲート） |
| **Linter / Types**| Ruff, Mypy, ESLint | Ruff 0.16, Mypy 2.3 | 高速なPython静的解析・フォーマット・型検査 |

---

### 3.3 フロントエンド構成

フロントエンドは `frontend/` 配下に配置され、Vite + React 18 + TypeScript によるモダンなコンポーネント指向アーキテクチャを採用しています。

- **`src/App.tsx`**: アプリケーション全体のレイアウト制御、ヘッダー、制作モード切替、トースト通知管理。
- **`src/components/GeneratePanel.tsx`**: 作品基本設定、主人公プロファイル、冒頭入力フォーム、非同期ポーリング進行状況バーの制御。
- **`src/components/ExportPanel.tsx`**: 生成された小説本文のプレビュー、次話展開サジェスチョン Chips、納品ZIPダウンロードトリガー。
- **`src/components/GraphVisualization.tsx`**: ナレッジグラフ（登場人物相関・世界観ノード）の2Dフォースグラフ可視化。
- **`src/components/ReversePlotBuilder.tsx`**: 逆算プロットビルダー (4ステップ逆算プロット)。
- **`src/components/studio/`**: 上級者Studioコンポーネント群
  - `StudioWorkspace.tsx`: 3カラム統合ワークスペース
  - `ChapterOutlineTree.tsx`: 章構成ツリービュー
- **`src/components/editor/`**: エディタ機能コンポーネント群
  - `Editor.tsx`: 本文編集用リッチエディタ、文字数カウンタ、リアルタイム保存
  - `InlineAiToolbar.tsx`: インライン五感推敲ツールバー
  - `NextBeatsPanel.tsx`: 次の展開3案生成パネル
  - `EditorialSidebar.tsx`: 専属AI編集者(Q&A/矛盾診断)
  - `AiSuggestions.tsx`: AI提案ポップオーバー
  - `ConflictModal.tsx`: 設定矛盾モーダル
- **`src/components/AssetPackPanel.tsx`**: マルチメディアアセットパック進捗管理・ダウンロード
- **`src/components/common/ToastContainer.tsx`**: 非同期処理の成功・エラー・警告を画面右下に通知するトーストUI。
- **`src/api/easyMode.ts`**: バックエンドAPIとの通信層（生成リクエスト、ポーリング、ZIPダウンロード、企画ガチャ）。

---

### 3.4 バックエンド API 構成

FastAPI アプリケーション (`src/backend/server.py`) は、モジュールごとにルーターを分割し、依存性の注入 (`Depends`) を活用して疎結合を徹底しています。

- **`routers/easy_mode.py`**: かんたんモードの全エンドポイント（執筆、ポーリング、ZIP納品、ガチャ、ダイジェスト、昇格、IF分岐昇格）。
- **`routers/books.py`**: 作品 CRUD およびメタデータ管理。
- **`routers/plots.py`**: プロット CRUD およびプロットツリー操作。
- **`routers/episodes.py`**: エピソード CRUD および話数管理。
- **`routers/graph.py`**: ナレッジグラフのノード・エッジデータ取得およびエンティティ検索。
- **`routers/illustrations.py`**: 挿絵プロンプト生成および画像生成ジョブ管理。
- **`routers/marketing.py`**: マーケティング資料・あらすじ・キャッチコピー生成。
- **`routers/multimedia.py`** (`ENABLE_MULTIMEDIA`): シーン画像 / 立ち絵 / 表紙 / ボイス / BGM のアセットパック管理。
- **`routers/collab.py`**: コメントツリーと `ChapterVersion` (CRDT ベクタークロック) による共同編集 API。
- **`routers/prompt_versions.py`**: プロンプトのバージョン管理。
- **`routers/prompt_compare.py`**: プロンプト A/B 比較。
- **`routers/streaming.py`**: SSE による長文生成のリアルタイム配信。
- **`routers/export.py`**: eBook (EPUB) エクスポート・詳細エクスポート。
- **`routers/cost.py`**: コスト分析・トークン使用量追踪 API。
- **`routers/hooks.py`**: イベントフック(トリガー)管理 API。
- **`routers/issues.py`**: 品質監査で検知された問題(Issue)管理 API。
- **`routers/structure.py`**: 作品構造(章構成・プロットツリー)管理 API。
- **`routers/commercial.py`**: 商用展開・収益化設定管理 API。
- **`routers/patches.py`**: 自動修正パッチ(Patch)管理 API。
- **`routers/tasks.py`**: タスク状態管理・一覧取得 API。
- **`routers/misc.py`**: ユーティリティエンドポイント群。
- **`routers/novel.py`**: 小説詳細・メタデータ管理 API。
- **`routers/orchestrated.py`**: オーケストレーション統合 API。
- **`routers/trace.py`**: 実行トレース・ログ取得 API。
- **`routers/editor.py`**: 上級者Studioエディタ状態管理 API。
- **`routers/styles.py`**: 文体プリセット・スタイル管理 API。
- **`observability.py`**: `/health`（多段ヘルスチェック）および `/metrics`（プロセス内メトリクス）。
- **`rate_limit.py`**: IP単位スライディングウィンドウ方式による過剰リクエスト制限 (HTTP 429)。

---

### 3.5 非同期タスク実行基盤

時間のかかるAI生成処理は、FastAPIプロセスから完全に切り離され、Huey タスクキューで処理されます。

- **環境に応じた自動バックエンド切替 (`src/backend/tasks/huey.py`)**:
  - `HUEY_BACKEND=redis` の場合: `RedisHuey` を使用し、分散環境での高スループットキューイングを実現。
  - `HUEY_BACKEND=sqlite` の場合: `SqliteHuey` を使用し、外部サーバー不要のローカル実行を実現。
- **タスクステータス管理 (`src/backend/tasks/generation_tasks.py`)**:
  タスクの開始・完了・失敗はデータベースの `Task` テーブルへ即座に記録され、ワーカーがダウンした場合でも状態の追跡が可能です。

---

### 3.6 知識・永続化層

- **SQLAlchemy 2.0 ORM**: 全てのテーブル定義は型安全な宣言的マッピングで統一。
- **SQLite WAL モード**: ローカル実行時、`PRAGMA journal_mode=WAL` および `PRAGMA foreign_keys=ON` を自動適用し、同時読み書き性能とデータ整合性を最大化。
- **PostgreSQL 16 + Apache AGE + pgvector**: 本番環境において、リレーショナルデータ・ナレッジグラフ・ベクトル検索を単一インスタンスで統合（Docker イメージ `apache/age-postgresql:16-pgvector`）。
- **ChromaDB (オプション)**: 大規模コレクションを独立プロセスで保持したい場合に切替可能（`CHROMA_HOST` / `CHROMA_PORT`）。
- **マイグレーション**: スキーマ変更は Alembic で管理。`alembic.ini` の `script_location = src/backend/alembic`、実際のマイグレーションモジュールは `src/backend/alembic/versions/` に配置（`0000_initial_migration`, `0001_erotic_intensity`, `0002_add_catchcopy`, `0003_pgvector_chapter_chunks`, `0004_add_ai_assistant_config`, `0011_multimedia_artifacts`, `0012_age_graph_init`, `0013_graph_pipeline_idempotency`）。

---

## 4. マルチエージェント・オーケストレーション詳細

> 詳細設計: [`docs/UNIFIED_PIPELINE_IMPLEMENTATION_PLAN.md`](UNIFIED_PIPELINE_IMPLEMENTATION_PLAN.md) / [`docs/collab-hybrid-implementation-plan.md`](docs/collab-hybrid-implementation-plan.md)

### 4.1 エージェント群の責務分担

AutoNovel では、1つの巨大なプロンプトに全てを委ねるのではなく、専門化された複数のAIエージェントが協調して小説を制作します。
エージェント間のルーティングは `src/agents/orchestrator.py` の `AgentName` / `AgentContext` / `AgentResult` ベースのグラフで表現される。

 EventBus は2種類存在する:
 - **`src/agents/event_bus.py` EventBus**: エージェント間オーケストレーションイベント用 (in-process + Redis Pub/Sub)
 - **`src/shared/event_bus.py` UIEventType**: Streamlit UI 向けイベント種別定義 (kernels/ → streamlit_app/ 間のbridge)

```
                      +--------------------+
                      |   PlanningAgent    | <── 企画・コンセプト・ターゲット読者選定
                      +--------------------+
                                │
                                ▼
                      +--------------------+
                      |     PlotAgent      | <── 章別プロットツリー・テンション設計
                      +--------------------+
                                │
             ┌──────────────────┴──────────────────┐
             ▼                                     ▼
   +--------------------+                +--------------------+
   |     BibleAgent     |                | ContextBuilderAgent| <── GraphRAG+履歴から文脈抽出
   | (世界観/キャラ管理)  |                +--------------------+
   +--------------------+                          │
             │                                     ▼
             │                           +--------------------+
             └──────────────────────────>|    WritingAgent    | <── 本文執筆・描写展開
                                         +--------------------+
                                                   │
                                                   ▼
                                         +--------------------+
                                         |     AuditAgent     | <── 伏線・口調・カタルシス監査
                                         +--------------------+
                                                   │
                                ┌──────────────────┴──────────────────┐
                                ▼                                     ▼
                      +--------------------+                +--------------------+
                      | IllustrationAgent  |                |   MarketingAgent   |
                      |  (挿絵プロンプト)   |                | (納品ZIP/あらすじ)  |
                      +--------------------+                +--------------------+
```

> **StreamPlotScheduler (`src/agents/writing_scheduler.py`) + `EpisodePipeline` (`src/agents/episode_pipeline.py`)**: 章単位の生成をストリーム配信・チェックポイント保存で進行させ、長文でも停止・再開可能。

### 4.1.5 ワークフロー層 (Workflows Layer)

`src/backend/workflows/` には、LangGraph ベースのステートグラフワークフローが19種類定義されている。
これらは agents/ と services/ を繋ぐ 중재レイヤーとして機能し、複雑な 멀티エージェント協調を宣言的に定義する。

| ワークフロー | ファイル | 用途 |
|-------------|----------|------|
| **Easy Mode Workflow** | `easy_mode_workflow.py` | かんたんモードの全体流程管理 |
| **Full Auto Workflow** | `full_auto_workflow.py` | 完全自動執筆の全体流程管理 |
| **Episode Writing Workflow** | `episode_writing_workflow.py` | 単一エピソード執筆流程 |
| **Plot Expansion Workflow** | `plot_expansion_workflow.py` | プロット展開流程 |
| **Plot Rebuild Workflow** | `plot_rebuild_workflow.py` | プロット大規模リビルド |
| **Reverse Plot Workflow** | `reverse_plot_workflow.py` | 逆算プロット生成 |
| **Critique Optimization Workflow** | `critique_optimization_workflow.py` | 批評ベース最適化 |
| **Illustration Workflow** | `illustration_workflow.py` | 挿絵生成流程 |
| **Marketing Generation Workflow** | `marketing_generation_workflow.py` | マーケティング資料生成 |
| **Logical Audit Workflow** | `logical_audit_workflow.py` | 論理的整合性監査 |
| **Refine Erotic Workflow** | `refine_erotic_workflow.py` | エロティック整合性調整 |
| **Retry Failed Episodes Workflow** | `retry_failed_episodes_workflow.py` | 失敗エピソード再実行 |
| **Commercial Pipeline** | `commercial_pipeline.py` | 商用展開統合パイプライン |
| **Chapter Import Workflow** | `chapter_import_workflow.py` | 章インポート流程 |
| **Plan Generation Workflow** | `plan_generation_workflow.py` | 企画生成流程 |
| **Plot LangGraph** | `plot_langgraph.py` | LangGraph プロット状態グラフ |
| **Writing LangGraph** | `writing_langgraph.py` | LangGraph 執筆状態グラフ (32KB) |
| **Quality Metrics** | `quality_metrics.py` | 品質スコアリング算出 |
| **Base Workflow** | `base_workflow.py` | ワークフロー抽象基底クラス |

> **Graph State (`graph_state.py`)**: ワークフロー間の共有グラフ状態管理
> **DAG Builder (`dag_builder.py`)**: ワークフロー DAG 動的構築ユーティリティ
> **Shared Ops (`_shared_ops.py`)**: ワークフロー間共有演算ユーティリティ

---

### 4.2 専門エージェント詳細

#### 1. `PlanningAgent` (`src/agents/planning.py`)
- **役割**: 作品全体のコンセプト、想定読者層、テーマ性、全話ボリューム（例: 全50話）、商業的フックを設計。
- **機能**: トレンド分析、3案企画ガチャの生成、ログライン策定。

#### 2. `PlotAgent` (`src/agents/plot.py`)
- **役割**: エピソードごとのあらすじ、テンション変動（Tension Delta）、カタルシス種別、伏線配置を計画。
- **機能**: プロットツリー構築、読者引き込み（Next Hook）設計、動的プロットリビルド。

#### 3. `BibleAgent` (`src/agents/bible.py`, `src/services/bible_service.py`)
- **役割**: 作品の世界観設定、地理・魔法体系・勢力図、登場人物プロファイルを一元管理。
- **機能**: 本文からの新設定・新登場人物の自動検出、設定変更の差分マージと矛盾警告。

#### 4. `ContextBuilderAgent` (`src/agents/context_builder_agent.py`)
- **役割**: 次の章を執筆するために必要な情報のみを厳選し、LLMのコンテキストウィンドウに最適化してプロンプトを合成。
- **機能**: 直近のダイジェスト、関連する世界観ルール、関係するキャラクター情報、伏線ステータスを GraphRAG 経由で統合。`ContextBuilder` (旧 `context_builder.py`) は互換ラッパとして非推奨化済み。
- **関連**: `src/services/episode_context.py`（エピソード単位の軽量コンテキスト） / `src/agents/prompt_composer.py`（テンプレ合成）。

#### 5. `WritingAgent` / `EpisodeWriter` (`src/agents/writing/writing.py`, `src/services/episode_writer.py`)
- **役割**: コンテキストとプロットに基づき、臨場感ある情景描写・感情豊かな会話文・迫力ある戦闘シーンを執筆。
- **機能**: 文体DNAの遵守、視点（一人称/三人称）の一貫性保持、指定文字数範囲での過不足ない着地。
- **Orchestrator 連携**: `run(ctx: AgentContext) -> AgentResult` シグネチャで `next_agent=AgentName.AUDIT` へ自動遷移。

#### 6. `AuditAgent` (`src/agents/audit_agent.py`)
- **役割**: 執筆された本文を厳格に検査し、品質スコアを算出。`LogicalAuditor`（論理整合性）+ `DeAIAuditor`（AI 臭除去）+ シャープエッジ監査を束ねたファサード。
- **機能**: 伏線回収チェック、キャラクター口調崩れの検出、カタルシス達成度判定、自動修正パッチ提案。
- **サブモジュール**: `src/agents/audit.py`（内部クラス群）、`src/agents/sharp_edge_preserver`、`src/agents/early_entertainment_checker`、`src/agents/diversity_scorer`。

#### 7. `IllustrationAgent` (`src/agents/illustration_agent.py`)
- **役割**: 本文中のハイライトシーンを特定し、AI画像生成用の精密な英語プロンプトを構築。
- **機能**: キャラクターの外見タグ（髪型、服装、表情）と背景・ライティング設定の自動マージ。

#### 8. `MarketingAgent` (`src/agents/marketing.py`, `src/services/marketing.py`)
- **役割**: 読者を惹きつけるキャッチコピー、Web投稿用あらすじ、メタデータ、納品パッケージ（ZIP）を生成。

---

### 4.3 マルチエージェント協調シーケンス

8 つのエージェントが **Orchestrator**（`src/agents/orchestrator.py`）によって順序実行され、各エージェントの実行前後には **EventBus**（`src/agents/event_bus.py`）がイベントを発行します。

```mermaid
sequenceDiagram
    autonumber
    actor User as ユーザー
    participant Orch as Orchestrator
    participant Bus as EventBus
    participant Planning as PlanningAgent
    participant Plot as PlotAgent
    participant Bible as BibleAgent
    participant Ctx as ContextBuilderAgent
    participant Writer as WritingAgent
    participant Audit as AuditAgent
    participant Illust as IllustrationAgent
    participant Market as MarketingAgent

    User->>Orch: 起動 (PLANNING から)
    Orch->>Bus: planning.started
    Orch->>Planning: run(ctx)
    Planning-->>Orch: AgentResult(arcs, next=PLOT)
    Orch->>Bus: planning.completed

    Orch->>Bus: plot.started
    Orch->>Plot: run(ctx)
    Plot-->>Orch: AgentResult(plots, next=BIBLE)
    Orch->>Bus: plot.completed

    Orch->>Bus: bible.started
    Orch->>Bible: run(ctx)
    Bible-->>Orch: AgentResult(bible, next=CONTEXT_BUILDER)
    Orch->>Bus: bible.completed

    Orch->>Bus: context_builder.started
    Orch->>Ctx: run(ctx)
    Ctx-->>Orch: AgentResult(writing_context, next=WRITING)
    Orch->>Bus: context_builder.completed

    Orch->>Bus: writing.started
    Orch->>Writer: run(ctx)
    Writer-->>Orch: AgentResult(drafted_text, next=AUDIT)
    Orch->>Bus: writing.completed

    Orch->>Bus: audit.started
    Orch->>Audit: run(ctx)
    alt 監査合格
        Audit-->>Orch: AgentResult(audit_report, next=ILLUSTRATION)
        Orch->>Bus: audit.completed
        Orch->>Bus: illustration.started
        Orch->>Illust: run(ctx)
        Illust-->>Orch: AgentResult(illustrations, next=MARKETING)
        Orch->>Bus: illustration.completed
    else 監査不合格 (should_retry)
        Audit-->>Orch: AgentResult(should_retry=true, next=WRITING)
        Orch->>Bus: audit.completed (failed)
        Orch->>Writer: 再実行
    end

    Orch->>Bus: marketing.started
    Orch->>Market: run(ctx)
    Market-->>Orch: AgentResult(zip_data, next=None)
    Orch->>Bus: marketing.completed
    Orch-->>User: 完了 (zip_data 返却)
```

#### 制御フロー詳細

各エージェントは `AgentResult(next_agent, artifacts, should_retry, error)` を返します。`Orchestrator` は以下のように動作します：

1. `next_agent` が指定されていれば次のエージェントへ遷移
2. `should_retry=True` なら同じエージェントを再実行（リトライループ）
3. `error` が設定されていれば `RuntimeError` を送出
4. `next_agent=None` で終了

#### API エンドポイント

| メソッド | パス | 説明 |
|:---|:---|:---|
| `POST` | `/orchestrated/generate` | オーケストレーション生成タスクをキュー投入 (Huey) |
| `GET` | `/orchestrated/status/{task_id}` | タスクステータスポーリング |
| `GET` | `/orchestrated/export/{book_id}` | ZIP エクスポート |
| `DELETE` | `/orchestrated/task/{task_id}` | タスクキャンセル |

#### 環境変数（Redis Streams 連携）

| 変数 | デフォルト | 説明 |
|:---|:---|:---|
| `USE_REDIS_EVENTS` | `false` | `true` で EventBus が Redis Streams にイベント発行 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 接続文字列 |
| `REDIS_MAX_CONNECTIONS` | `50` | 接続プール最大数 |

---

## 5. GraphRAG & 長期記憶・コンテキストマネジメント

長編小説制作における最大の敵は「過去の設定を忘れること」です。AutoNovel は **GraphRAG（Graph + Retrieval-Augmented Generation）** により、この問題を根本から解決しています。
**PostgreSQL + Apache AGE + pgvector** を単一インスタンスで運用し、抽出・埋め込み・再ランキングを非同期パイプラインで束ねます。

> 詳細なセットアップ手順 (ChromaDB / pgvector / Reranker) は
> [`docs/rag_setup.md`](docs/rag_setup.md) を参照してください。

```
+-----------------------------------------------------------------------------------+
|                         GraphRAG 統合記憶アーキテクチャ                            |
|                                                                                   |
|  [エピソード本文生成] ──> [Chunk分割] ──> [埋め込み (Embedding Service)]           |
|                                          │                                        |
|                                          ├──> [pgvector / ChromaDB] (chunk)     |
|                                          │     - 過去シーン・世界観テキスト       |
|                                          │                                        |
|                                          └──> [Apache AGE ナレッジグラフ]         |
|                                                - キャラクター相関 (好感度/敵対)  |
|                                                - アイテム所持・能力獲得状態        |
|                                                - 地理・所属組織の依存関係         |
|                                                                                   |
|  [次話プロンプト生成時] <── [RRF ハイブリッド検索 (vector + tsvector + graph)      |
|                            + cross-encoder reranker] <────────────────────────┘
+-----------------------------------------------------------------------------------+
```

### 5.1 動的世界観Bible管理とエンティティ抽出

エピソードが執筆されるたびに、`graph_pipeline.py` がチャンク化 → 埋め込み → `extraction_service` でエンティティ・関係性を抽出し、**チャンク upsert と AGE への Cypher 適用を単一トランザクション**で実行します（`0013_graph_pipeline_idempotency` により冪等性キーを保証）。
更新と同時に以下の情報が `BibleService` 経由で整理されます：

- **登場人物のステータス変化**: HP/魔力、負傷状態、獲得した新スキル、装備品。
- **人間関係の変動**: 「AがBを裏切った」「CがDに好意を抱いた」などの関係性エッジ更新。
- **世界観設定の開示 (Revealed Settings)**: 作中で初めて明かされた伝承や地名をBibleの `revealed` フィールドへ追加。

### 5.2 ナレッジグラフとベクトルストアのハイブリッド検索

次話の執筆時、`GraphRAGService.build_rag_context()` (`src/services/rag_service.py`) が3系統の検索を統合します：

1. **ベクトル検索 (pgvector / ChromaDB)**: 現在のプロット概要とコサイン類似度が高いチャンクを `search_with_score(min_score=…)` で取得。
2. **全文検索 (PostgreSQL `tsvector` / BM25)**: 固有名詞や口語表現の語彙一致を補強。
3. **グラフ走査 (Apache AGE openCypher)**: 現在のシーンに登場するキャラクターを起点に深さ2ホップ以内の関係性エッジを抽出。

3系統のスコアを **Reciprocal Rank Fusion (RRF)** でマージし、`reranker.py`（cross-encoder もしくは simple）の `top_k` を通過させた結果をトークン予算に合わせて整形、`graph_context` / `vector_context` としてプロンプトへ注入します。

### 5.3 コンテキストウィンドウ管理 & セマンティックキャッシュ

- **`ContextWindowManager` (`src/core/context_window_manager.py`)**:
  LLMの最大トークン長（Context Window）を超過しないよう、重要度スコア（Recency, Relevance, Importance）に基づいて情報を動的にプルーニング。
- **セマンティックキャッシュ (`src/services/semantic_cache.py`, `prompt_caching.py`)**:
  同一または類似の埋め込みクエリに対し、過去の推論結果を再利用することで API コストを最大 40% 削減。
- **プロンプトバージョン管理 (`src/services/prompt_registry.py` + `routers/prompt_versions.py`)**:
  本番投入中のプロンプトを版管理し、A/B 比較 (`prompt_compare.py`) で品質メトリクスを追跡。

---

## 6. 非同期パイプライン & ライフサイクル管理

### 6.1 タスクステートマシン

AutoNovel の生成タスクは、明確に定義されたステートマシンに従って遷移します。

```mermaid
stateDiagram-v2
    [*] --> pending: POST /easy_mode/generate (キュー投入)
    pending --> running: Huey ワーカーがデキュー
    running --> completed: LLM生成 & GraphRAG更新 成功
    running --> failed: APIエラー / タイムアウト / 例外
    pending --> cancelled: DELETE /easy_mode/task/{id}
    running --> cancelled: DELETE /easy_mode/task/{id}
    completed --> [*]
    failed --> [*]
    cancelled --> [*]
```

- **`pending`**: タスクがキューに積まれ、ワーカーの処理開始を待機している状態。
- **`running`**: ワーカーがタスクを取得し、LLM推論およびナレッジグラフ更新を実行中。
- **`completed`**: 生成が正常終了し、本文・サジェスチョン・所要時間がDBに保存された状態。
- **`failed`**: エラーが発生し、エラーメッセージが記録された状態。
- **`cancelled`**: ユーザーによって生成処理が明示的に中断された状態。

---

### 6.2 非同期生成・ステータスポーリングシーケンス

```mermaid
sequenceDiagram
    autonumber
    actor Client as ブラウザ (React UI)
    participant Server as FastAPI サーバー
    participant Queue as Huey キュー (Redis/SQLite)
    participant Worker as Huey ワーカー
    participant DB as データベース (SQLAlchemy)
    participant LLM as LLM サービス

    Client->>Server: POST /easy_mode/generate (入力設定)
    Server->>Server: レートリミット検証 (IP単位)
    Server->>DB: Task レコード作成 (status: "running")
    Server->>Queue: generate_chapter_task をエンキュー
    Server-->>Client: 200 OK (task_id 返却)

    loop ポーリング (1.5秒間隔 / 最大40回)
        Client->>Server: GET /easy_mode/status/{task_id}
        Server->>Queue: huey.result(task_id) を確認
        alt まだ処理中
            Server-->>Client: {"status": "pending"}
        else 処理完了
            Server-->>Client: {"status": "completed", "result": {...}}
        else 失敗
            Server-->>Client: {"status": "failed", "error": "..."}
        end
    end

    par バックグラウンド実行
        Queue->>Worker: タスクをデキュー
        Worker->>LLM: プロンプト投入 & 本文生成
        LLM-->>Worker: 本文テキスト & 次話提案返却
        Worker->>DB: ナレッジグラフ更新 & タスク完了保存
        Worker->>Worker: メトリクス更新 (tasks_completed)
    end

    Client->>Server: GET /easy_mode/export/{book_id}
    Server->>DB: 作品データ一式取得
    Server->>Server: MarketingAgent によるZIP生成
    Server-->>Client: 200 OK (application/zip ストリーミング)
```

---

### 6.3 トランザクション保護とフォールバック保証

- **多重安全トランザクション**:
  DBセッション操作はコンテキストマネージャにより保護され、例外発生時は即座に `session.rollback()` が実行され、孤立レコードの発生を防止。
- **エクスポートのフォールバック保証 (TC-12準拠)**:
  万一、指定された `book_id` のデータがDBに存在しない場合でも、システムが自動的に標準フォールバックデータを注入して正常なZIPを生成・返却するため、展示デモやテスト環境でダウンロードが失敗することはありません。

---

## 7. データモデル & ER設計

### 7.1 ドメインモデル ER図

SQLAlchemy 2.0 に基づく主要テーブルとリレーションシップです。

```mermaid
erDiagram
    BOOK ||--o{ BRANCH : "has branches"
    BOOK ||--o{ CHAPTER : "contains chapters"
    BOOK ||--o{ CHARACTER : "features characters"
    BOOK ||--o{ PLOT : "structured by plots"
    BOOK ||--o{ BIBLE : "defined by bible"
    BOOK ||--o{ ISSUE : "tracks issues"
    BOOK ||--o{ CHAPTER_VERSION : "collab history (CRDT)"
    CHAPTER_VERSION ||--o{ CHAPTER_VERSION : "base_version"
    BRANCH ||--o{ PLOT : "owns branch plots"
    ISSUE ||--o{ PATCH : "resolved by patches"

    BOOK {
        int id PK "作品ID"
        string title "タイトル"
        string genre "ジャンル"
        text synopsis "あらすじ"
        string catchcopy "キャッチコピー"
        int target_eps "目標話数"
        string style_dna "文体DNA"
        string status "状態 (draft/published)"
        int current_branch_id "現在ブランチID"
        int cumulative_tension "累積テンション"
        float cumulative_cost "累積推論コスト(USD)"
    }

    BRANCH {
        int id PK "ブランチID"
        int book_id FK "作品ID"
        string name "ブランチ名 (main/if_route)"
        int parent_id "親ブランチID"
        int fork_ep_num "分岐元話数"
    }

    CHAPTER {
        int id PK "章ID"
        int book_id FK "作品ID"
        int ep_num "話数"
        string title "サブタイトル"
        text content "章本文"
        bool is_anchor "アンカー章フラグ"
        datetime created_at "執筆日時"
    }

    CHARACTER {
        int id PK "キャラクターID"
        int book_id FK "作品ID"
        string name "名前"
        string role "役割 (主人公/ヒロイン/ライバル)"
        text personality "性格・行動指針"
        text ability "特殊能力・戦闘スタイル"
        string visual_dna "外見プロンプトDNA"
    }

    PLOT {
        int id PK "プロットID"
        int book_id FK "作品ID"
        int branch_id FK "ブランチID"
        int ep_num "対象話数"
        string title "プロット見出し"
        text one_line_summary "1行要約"
        text summary "詳細あらすじ"
        int tension "テンション値 (0-100)"
        bool is_catharsis "カタルシス到達フラグ"
        string catharsis_type "カタルシス種別"
        text next_hook "次話への引き"
    }

    BIBLE {
        int id PK "設定集ID"
        int book_id FK "作品ID"
        text settings "世界観JSON (地理/魔法/組織)"
        text revealed "作中開示済み設定"
        int version "設定バージョン"
    }

    CHAPTER_VERSION {
        int id PK "バージョンID"
        int book_id FK "作品ID"
        int chapter_ep "対象話数"
        string user_name "編集ユーザー名"
        text content "本文"
        json vector_clock "ベクタークロック (CRDT)"
        int base_version_id FK "親バージョンID"
        datetime created_at "作成日時"
    }

    TASK {
        int id PK "タスクID (Huey UUID)"
        string status "pending / running / completed / failed"
        text result "生成結果JSON"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }
```

---

### 7.2 主要エンティティ仕様

| モデル名 | テーブル名 | 主な役割 |
| :--- | :--- | :--- |
| **`Book`** | `books` | 小説プロジェクトのルートエンティティ。タイトル、ジャンル、文体DNA、累積コストを保持。 |
| **`Branch`** | `branches` | プロットの分岐ルート。Gitのように本編（main）とIF分岐を階層管理。 |
| **`Chapter`** | `chapters` | 執筆完了した各話の本文データ。話数、サブタイトル、アンカー固定フラグを保持。 |
| **`Character`** | `characters` | 登場人物シート。名前、性格、能力、外見プロンプトDNAを保持。 |
| **`Plot`** | `plots` | 各話の設計図。1行要約、目標テンション、カタルシス種別、読者フックを保持。 |
| **`Bible`** | `bibles` | 世界観・魔法体系・歴史・地理などの設定辞書（JSON形式）と開示状況。 |
| **`ChapterVersion`** | `chapter_versions` | 共同編集のための章リビジョン。`vector_clock` (JSON) と `base_version_id` で CRDT マージ。 |
| **`Comment` / `ProjectMember`** | `comments`, `project_members` | 章単位のスレッドコメントとプロジェクトメンバー管理。 |
| **`MultimediaArtifact` / `MultimediaTask`** | `multimedia_artifacts`, `multimedia_tasks` | シーン画像 / 立ち絵 / 表紙 / ボイス / BGM の生成結果と非同期タスク。 |
| **`Task`** | `tasks` | 非同期執筆タスクのステータス追跡・結果保存。 |
| **`Issue` / `Patch`** | `issues`, `patches` | 監査エージェントが検知した設定矛盾（Issue）と、その自動修正提案（Patch）。 |

---

## 8. ディレクトリ構成 & コードベースマップ

### 8.1 全体ディレクトリツリー

```
.
├── src/                               # バックエンド Python ソースコード
│   ├── backend/                       # FastAPI Web API レイヤー
│   │   ├── server.py                  # FastAPI アプリケーション定義・ミドルウェア・ルーティング
│   │   ├── rate_limit.py              # IP単位スライディングウィンドウ・レートリミッター
│   │   ├── observability.py           # ヘルスチェック (/health) & メトリクス (/metrics)
│   │   ├── logging_config.py          # 構造化 JSON / テキストログ設定
│   │   ├── exceptions.py              # カスタム例外階層定義
│   │   ├── config.py                  # 設定クラス (Pydantic Settings)
│   │   ├── database/                  # DBアクセス層
│   │   │   ├── __init__.py            # Engine, SessionLocal, get_db(), init_db()
│   │   │   ├── models.py              # SQLAlchemy 2.0 ORM モデル定義 (35+ モデル)
│   │   │   ├── repository.py          # BookRepository (トランザクション & クエリ集約)
│   │   │   └── repositories/, uow.py  # リポジトリ & Unit of Work
│   │   ├── alembic/                   # Alembic マイグレーション環境 (versions/ 配下にマイグレーションファイル)
│   │   ├── routers/                   # API ルーター群 (31)
│   │   │   ├── easy_mode.py           # かんたんモード API (生成/ポーリング/ZIP納品/ガチャ/昇格)
│   │   │   ├── books.py               # 作品 CRUD
│   │   │   ├── plots.py               # プロット CRUD
│   │   │   ├── episodes.py            # エピソード CRUD
│   │   │   ├── graph.py               # ナレッジグラフデータ提供 API
│   │   │   ├── illustrations.py       # 挿絵プロンプト生成
│   │   │   ├── marketing.py           # マーケティング資料生成
│   │   │   ├── multimedia.py          # マルチメディアアセットパック API (ENABLE_MULTIMEDIA)
│   │   │   ├── collab.py              # 共同編集 (ChapterVersion / Comments)
│   │   │   ├── prompt_versions.py     # プロンプトバージョン管理
│   │   │   ├── prompt_compare.py      # プロンプト A/B 比較
│   │   │   ├── export.py              # eBook (EPUB) エクスポート
│   │   │   ├── streaming.py           # SSE リアルタイムストリーミング
│   │   │   ├── cost.py               # コスト分析・トークン追跡
│   │   │   ├── hooks.py              # イベントフック管理
│   │   │   ├── issues.py            # 品質Issue管理
│   │   │   ├── structure.py         # 作品構造管理
│   │   │   ├── commercial.py         # 商用展開設定
│   │   │   ├── patches.py          # 自動修正パッチ管理
│   │   │   ├── tasks.py            # タスク状態管理
│   │   │   ├── misc.py             # ユーティリティ群
│   │   │   ├── novel.py           # 小説詳細・メタデータ
│   │   │   ├── orchestrated.py    # オーケストレーション統合
│   │   │   ├── trace.py           # 実行トレース取得
│   │   │   ├── editor.py          # Studioエディタ状態管理
│   │   │   ├── styles.py          # 文体プリセット管理
│   │   │   ├── health.py          # ヘルスチェック
│   │   │   └── __init__.py
│   │   ├── tasks/                     # 非同期キューイング層
│   │   │   ├── huey.py                # Huey インスタンス (Redis / SQLite 自動切替)
│   │   │   ├── generation_tasks.py    # 非同期生成ワーカータスク
│   │   │   ├── illustration_tasks.py, multimedia_tasks.py
│   │   ├── workflows/                 # LangGraph ワークフロー (19種類)
│   │   │   ├── base_workflow.py       # ワークフロー抽象基底クラス
│   │   │   ├── easy_mode_workflow.py  # かんたんモード統合ワークフロー
│   │   │   ├── full_auto_workflow.py  # 完全自動執筆ワークフロー
│   │   │   ├── episode_writing_workflow.py  # エピソード執筆ワークフロー
│   │   │   ├── plot_expansion_workflow.py   # プロット展開ワークフロー
│   │   │   ├── plot_rebuild_workflow.py     # プロットリビルドワークフロー
│   │   │   ├── reverse_plot_workflow.py     # 逆算プロットワークフロー
│   │   │   ├── critique_optimization_workflow.py  # 批評最適化ワークフロー
│   │   │   ├── illustration_workflow.py     # 挿絵生成ワークフロー
│   │   │   ├── marketing_generation_workflow.py  # マーケティング生成
│   │   │   ├── logical_audit_workflow.py   # 論理的監査ワークフロー
│   │   │   ├── refine_erotic_workflow.py   # エロティック整合性ワークフロー
│   │   │   ├── retry_failed_episodes_workflow.py  # 失敗リトライ
│   │   │   ├── commercial_pipeline.py  # 商用展開パイプライン
│   │   │   ├── chapter_import_workflow.py  # 章インポートワークフロー
│   │   │   ├── plan_generation_workflow.py  # 企画生成ワークフロー
│   │   │   ├── plot_langgraph.py     # LangGraph プロット状態グラフ
│   │   │   ├── writing_langgraph.py   # LangGraph 執筆状態グラフ
│   │   │   ├── graph_state.py         # グラフ状態管理
│   │   │   ├── dag_builder.py         # DAG ビルダー
│   │   │   ├── quality_metrics.py     # 品質メトリクス計算
│   │   │   ├── _shared_ops.py         # 共有演算ユーティリティ
│   │   │   └── __init__.py
│   │   └── engine*.py, tension_*.py   # エンジン / テンション制御
│   │
│   ├── agents/                        # マルチエージェント知能層
│   │   ├── base.py                    # BaseAgent 抽象基底
│   │   ├── orchestrator.py            # AgentName/AgentContext/AgentResult ルーター
│   │   ├── event_bus.py               # エージェント間 EventBus (in-process + Redis pub/sub)
│   │   ├── episode_pipeline.py        # エピソード執筆パイプライン (ストリーム配信/チェックポイント)
│   │   ├── writing/                   # WritingAgent + episode_writer, bible_extractor, rewrite_orchestrator
│   │   ├── planning.py                # 全体構成 & 企画エージェント
│   │   ├── plot.py                    # プロット策定 & リビルドエージェント
│   │   ├── bible.py                   # 世界観設定エージェント
│   │   ├── context_builder_agent.py   # 執筆コンテキスト合成（新）
│   │   ├── context_builder.py         # 旧実装（互換ラッパ、非推奨）
│   │   ├── audit_agent.py             # AuditAgent ファサード (logical + de-AI + sharp-edge)
│   │   ├── audit.py                   # 内部監査クラス群
│   │   ├── illustration_agent.py      # 挿絵プロンプト生成エージェント
│   │   ├── marketing.py               # マーケティング支援エージェント
│   │   ├── writing_scheduler.py       # StreamingPlotScheduler
│   │   └── erotic/                    # エロティック整合性サブモジュール (vocabulary/curve/...)
│   │
│   ├── services/                      # ドメインサービス & 外部連携層 (~80 モジュール)
│   │   ├── llm_service.py             # LLM 呼び出しラッパ (Gemini / OpenAI 互換)
│   │   ├── llm/                       # LLM アダプタ群 (base/factory/openai/gemini/mock/retry)
│   │   ├── rag_service.py             # GraphRAGService (vector + graph + tsvector → RRF)
│   │   ├── graph_pipeline.py          # Apache AGE ナレッジグラフ抽出パイプライン
│   │   ├── age_client.py              # Apache AGE クライアント (Cypher / agtype / プール)
│   │   ├── vector_store.py            # ChromaDB / pgvector / In-Memory / BM25
│   │   ├── embedding_service.py, reranker.py
│   │   ├── extraction_service.py      # chapter→knowledge-graph 抽出 (few-shot / multi-pass)
│   │   ├── digest_service.py, gacha_service.py
│   │   ├── marketing.py, illustration/(character,cover,scene)
│   │   ├── image_service.py           # Google GenAI Imagen
│   │   ├── auto_workflow_pipeline.py, pipeline_base.py, pipeline_steps.py
│   │   ├── pipeline_param_mapper.py, unified_pipeline_config.py
│   │   ├── semantic_cache.py, prompt_caching.py, redis_cache.py
│   │   ├── prompt_registry.py, prompt_version_service.py, prompt_comparison.py
│   │   └── cost_analytics.py, token_tracker.py, audit_service.py, ...
│   │
│   ├── infrastructure/                # 横断インフラ (database models, kaku DI container, ...)
│   ├── kernels/                       # 推論カーネル群 (enigma/hegemony/resonance/serenity/...)
│   ├── core/                          # コア共通基盤 (コンテキスト管理, A/Bテスト, プラグイン)
│   ├── domain/                        # 純粋ドメインエンティティ & 値オブジェクト
│   ├── engine/                        # パイプライン制御のサブシステム
│   ├── easy_mode/                     # かんたんモード補助モジュール
│   ├── llm/                           # 統合 LLM クライアント (services.llm の代替エントリ)
│   ├── models/                        # Pydantic 入出力スキーマ
│   ├── shared/                        # 共有ユーティリティ (resilience / circuit_breaker / safe_replace)
│   │   └── event_bus.py               # UIイベント型 (kernels → streamlit_app bridge)
│   ├── cli/                           # CLI エントリ (illustration_cli, promptops)
│   └── presets/                       # 文体・ジャンルプリセット
│
├── streamlit_app/                     # 代替 UI (Streamlit)
│   ├── 00_Settings.py                 # 設定ページ
│   └── 01_Home.py                     # ダッシュボード / ホーム
│
├── frontend/                          # フロントエンド React アプリケーション
│   ├── src/
│   │   ├── App.tsx                    # メインレイアウト & トースト管理
│   │   ├── index.css                  # デザインシステム (変数, アニメーション, UI)
│   │   ├── api/easyMode.ts            # バックエンド API 通信クライアント
│   │   ├── components/
│   │   │   ├── GeneratePanel.tsx      # 入力フォーム & ポーリング進行制御
│   │   │   ├── ExportPanel.tsx        # プレビュー表示 & ZIP エクスポート
│   │   │   ├── GraphVisualization.tsx # react-force-graph-2d ベース
│   │   │   ├── ReversePlotBuilder.tsx # 逆算プロットビルダー
│   │   │   ├── AssetPackPanel.tsx     # アセットパック進捗管理
│   │   │   ├── studio/               # 上級者Studioコンポーネント群
│   │   │   │   ├── StudioWorkspace.tsx  # 3カラム統合ワークスペース
│   │   │   │   └── ChapterOutlineTree.tsx  # 章構成ツリービュー
│   │   │   ├── editor/               # エディタ機能コンポーネント群
│   │   │   │   ├── Editor.tsx        # 本文編集用リッチエディタ
│   │   │   │   ├── InlineAiToolbar.tsx  # インライン五感推敲ツールバー
│   │   │   │   ├── NextBeatsPanel.tsx   # 次の展開3案生成
│   │   │   │   ├── EditorialSidebar.tsx # 専属AI編集者
│   │   │   │   ├── AiSuggestions.tsx    # AI提案ポップオーバー
│   │   │   │   └── ConflictModal.tsx   # 設定矛盾モーダル
│   │   │   └── common/Toast.tsx
│   │   └── types/easyMode.ts          # TypeScript 型定義
│   ├── tests/                         # Vitest + React Testing Library + MSW
│   ├── package.json                   # npm 依存パッケージ定義 (v4.0.0)
│   └── vite.config.ts                 # Vite 設定 & プロキシ設定
│
├── alembic/                           # ルート Alembic マイグレーション (実体)
│   └── versions/                      # 00000000_initial / 0001_erotic / 0002 / 0003_pgvector / 0011_mm / 0012_age / 0013_idempotency
│
├── tests/                             # バックエンドテストスイート (pytest)
│   ├── conftest.py                    # 共通テストフィクスチャ (real_db_manager 等)
│   ├── unit/                          # 単体テスト (~60 ファイル)
│   ├── integration/                   # 統合テスト (graphrag_age, streaming, multimedia_e2e...)
│   ├── perf/                          # パフォーマンステスト
│   ├── fixtures/, mocks/, shared/     # フィクスチャ・モック
│
├── scripts/                           # 自動化 & 運用スクリプト
│   ├── verify_all.ps1                 # 全品質ゲート一括実行
│   ├── smoke_test.ps1                 # E2E スモークテスト
│   └── generate_openapi.py            # docs/openapi.json 再生成
│
├── docs/                              # ドキュメント & 仕様書
│   ├── api.md, openapi.json           # REST API 仕様
│   ├── rag_setup.md                   # RAG セットアップ
│   ├── multimedia.md, multimedia_security.md, multimedia_slo.md
│   ├── collab-hybrid-implementation-plan.md
│   ├── streaming-migration.md, streaming-sse-plan.md
│   ├── term-mapping.md, easy_mode_suite.md, implementation_plan.md
│   ├── user/                          # ユーザー向けガイド
│   └── demo.gif
│
├── docker-compose.yml                 # 開発用 Docker Compose (ホットリロード対応)
├── docker-compose.prod.yml            # 本番用 Docker Compose (Nginx + Postgres + Redis)
├── Dockerfile                         # バックエンド用マルチステージ Dockerfile (python:3.12-slim)
├── frontend/Dockerfile                # Vite dev / Nginx production
├── Makefile                           # 開発コマンド集
├── pyproject.toml                     # Python ツール設定 (ruff 0.16, mypy 2.3, pytest, project v4.0.0)
├── requirements.txt                   # 本番 Python 依存パッケージ
├── alembic.ini                        # script_location = src/backend/alembic
├── アプリ起動.bat                     # Windows ワンクリック起動バッチ (Docker版)
└── アプリ起動_ローカル.bat            # Windows ワンクリック起動バッチ (ローカル版)
```

---

### 8.2 レイヤー責務と境界設計

- **API Layer (`src/backend/routers`)**:
  HTTPリクエストの受付、Pydanticによる型バリデーション、レートリミットチェック、非同期タスクのエンキューを担当。ビジネスロジックは直接記述せず、サービス層へ委譲。
- **Task Queue Layer (`src/backend/tasks`)**:
  バックグラウンドワーカーの実行ループ、リトライ制御、タスク状態のDB記録を担当。
- **Service Layer (`src/services`, `src/agents`)**:
  小説生成、GraphRAG抽出、プロット計算、品質監査、ZIPアーカイブ生成などの中核ドメインロジックを集約。
- **Repository / Database Layer (`src/backend/database`)**:
  SQLAlchemy 2.0 ORM モデルの管理、トランザクションのコミット/ロールバック、クエリ最適化を担当。

---

## 9. 必要動作環境

| 項目 | 最小要件 | 推奨環境 | 備考 |
| :--- | :--- | :--- | :--- |
| **Python** | 3.12 以上 | 3.12.x / 3.13.x | 型ヒント新構文およびパフォーマンス改善のため |
| **Node.js** | 18.x LTS 以上 | 20.x / 22.x LTS | フロントエンドビルドおよび Vitest 実行時 |
| **Docker** | 24.0 以上 | 最新 Docker Desktop | コンテナ構成でのワンクリック起動時 |
| **Docker Compose**| v2.20 以上 | 最新 `docker compose` | Compose V2 構文に対応 |
| **OS** | Windows 10/11, macOS, Linux | Windows 11 / Ubuntu 22.04 | PowerShell 7+ または bash 推奨 |
| **メモリ** | 4 GB 以上 | 8 GB 〜 16 GB | Docker コンテナ複数起動時 |

---

## 10. クイックスタート & 起動ガイド

### 10.1 Windows ワンクリック起動

Windows 環境をお使いの場合、リポジトリルートにあるバッチファイルをダブルクリックするだけで環境が自動起動します。

1. **`アプリ起動.bat`** (推奨 / Docker Compose 構成)
   - Docker Compose を利用してバックエンド、Huey ワーカー、React フロントエンド、PostgreSQL 16、Redis 7 を一括起動します。
   - 起動完了後、自動的にブラウザで `http://localhost:5173` が開きます。
2. **`アプリ起動_ローカル.bat`** (軽量 / ローカル Python + SQLite 構成)
   - Docker を起動せず、ローカルの Python 仮想環境 (`.venv`) と SQLite で超軽量に起動します。

---

### 10.2 Docker Compose による起動

#### 開発環境 (ホットリロード有効)
フロントエンド・バックエンドのソースコード変更が即座に反映されます。

```bash
# コンテナのビルドと起動
docker compose up --build

# 起動後のアクセス先:
# フロントエンド UI : http://localhost:5173
# FastAPI Swagger UI: http://localhost:8200/docs
```

#### 本番環境 (Nginx リバースプロキシ + PostgreSQL + Redis)
Nginx が静的アセットをキャッシュ配信し、APIリクエストを安全にルーティングします。

```bash
# 1. 本番用環境変数ファイルを作成
cp .env.example .env
# ※ .env を開き、POSTGRES_PASSWORD と REDIS_PASSWORD に強固なパスワードを設定してください

# 2. 本番コンテナ群をバックグラウンド起動
docker compose -f docker-compose.prod.yml up -d --build

# 起動後のアクセス先:
# 公開 Web アプリケーション: http://localhost:8080
# ヘルスチェック疎通確認: curl http://localhost:8080/health
```

停止コマンド:
```bash
docker compose down
# 本番の場合: docker compose -f docker-compose.prod.yml down
```

---

### 10.3 ローカル手動環境構築

ターミナルを個別に起動して開発・デバッグを行う場合の手順です。

```powershell
# ----------------------------------------------------
# 1. Python 仮想環境の作成と依存ライブラリのインストール
# ----------------------------------------------------
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements-dev.txt
py -m pip install -e .

# ----------------------------------------------------
# 2. フロントエンドの依存ライブラリのインストール
# ----------------------------------------------------
cd frontend
npm install
cd ..

# ----------------------------------------------------
# 3. ターミナル 1: バックエンド API 起動 (SQLite モード)
# ----------------------------------------------------
$env:HUEY_BACKEND = "sqlite"
$env:DATABASE_URL = "sqlite:///./autonovel.db"
py -m uvicorn src.backend.server:app --reload --port 8200

# ----------------------------------------------------
# 4. ターミナル 2: Huey キューワーカー起動
# ----------------------------------------------------
$env:HUEY_BACKEND = "sqlite"
$env:DATABASE_URL = "sqlite:///./autonovel.db"
py -m huey.bin.huey_consumer src.backend.tasks.huey.huey

# ----------------------------------------------------
# 5. ターミナル 3: React フロントエンド開発サーバー起動
# ----------------------------------------------------
cd frontend
npm run dev
# ブラウザで http://localhost:5173 を開く
```

---

## 11. 実践操作マニュアル & 納品パッケージ仕様

### 11.1 かんたんモード操作ステップ

```
[ステップ1: 設定入力] ──> [ステップ2: 執筆開始] ──> [ステップ3: プレビュー&提案] ──> [ステップ4: 納品ZIP保存]
```

1. **基本設定と主人公プロファイルの入力**:
   - **ジャンル選択**: 「ハイファンタジー」「ダークファンタジー」「異世界転生」「現代ダンジョン」等から選択。
   - **主人公の名前**: 例 `アルト`
   - **性格・特徴**: 例 `熱血・仲間思い・冷静な判断力`
   - **特殊能力・スキル**: 例 `古代魔導剣術・時空間把握`
   - **冒頭 / 前話プロンプト**: 例 `薄暗い迷宮の最深部、少年アルトは封印されし古代の魔剣を抜いた。`
2. **生成の実行**:
   - 「🪄 かんたん執筆開始」ボタンをクリック。
   - レート制限チェックを通過後、非同期キューへタスクが投入され、プログレスバーが進捗を表示します。
3. **プレビューと次話展開の確認**:
   - 生成が完了すると、右側ペインに約1500〜2000文字の本文が表示されます。
   - 下部に「💡 次話へのAI提案（3案）」が表示され、クリックすることで次話のプロンプトとして即座にセットできます。
4. **納品パッケージのダウンロード**:
   - 「📦 納品パッケージ (ZIP) ダウンロード」をクリックすると、`export_1.zip` が即座にダウンロードされます。

---

### 11.2 3案企画ガチャと上級者モード昇格

- **企画ガチャの回し方**:
  入力フォームの「🎲 3案ガチャ」ボタンを押すと、ジャンルに合わせた独自性あふれるプロット企画が3つ提示されます。気に入った企画を選ぶとフォームへ自動反映されます。
- **上級者モードへの昇格**:
  「🚀 アドバンスド作品へ昇格」ボタンを押すと、現在執筆中のストーリーデータが本格プロットツリー・世界観Bibleへと自動変換され、複数ブランチ執筆やGraphRAG管理が可能になります。

---

### 11.3 ナレッジグラフ可視化ツールの活用

画面上部の「🕸️ ナレッジグラフ」タブを開くと、執筆中に自動抽出されたキャラクターや世界観ノードの接続関係が物理シミュレーションで可視化されます。
- **ノードをクリック**: キャラクターの詳細設定（性格、能力、登場話数）を表示。
- **エッジにホバー**: 「敵対」「師弟」「好意」などの関係性プロパティを確認。

---

### 11.4 納品パッケージ (ZIP) の構造とフォーマット仕様

ダウンロードされるZIPファイル（例: `export_1.zip`）は、以下の規格に準拠した4つのファイルで構成されます：

```
export_1.zip
├── 01_本文.txt                      # 第1話〜最新話までの全エピソード統合テキスト
├── 02_キャラクター・世界観設定集.txt  # キャラクターシート ＆ 世界観設定 (Bible)
├── 03_プロット概要.txt              # 各話のあらすじ・1行要約・カタルシス一覧
└── 04_データダンプ.json             # 外部ツール・フロントエンド連携用完全JSON
```

#### 各ファイルの詳細仕様
1. **`01_本文.txt`**:
   - 各話の区切りに `【第N話：サブタイトル】` を自動挿入。
   - 空行調整・禁則処理・ルビ表記ルールを適用済み。
2. **`02_キャラクター・世界観設定集.txt`**:
   - 主人公・主要人物のプロファイル（名前、役割、性格、能力）。
   - 世界観Bibleに登録された地理、魔法体系、重要アイテムの設定テキスト。
3. **`03_プロット概要.txt`**:
   - 各エピソードの「話数」「サブタイトル」「1行ログライン」「あらすじ」「目標テンション」をリスト化。
4. **`04_データダンプ.json`**:
   - 作品メタデータ、全エピソード、キャラクター配列、プロット配列、世界観JSONを格納した構造化データ。

---

### 11.5 商用出版API連携 (なろう/カクヨム/Kobo/Kindle)

AutoNovelは生成した小説を、主要なWeb小説プラットフォームへ**直接投稿・更新**できます。

#### 対応プラットフォーム

| プラットフォーム | 方式 | 状態 | 必要認証 | レート制限 |
|----------------|------|------|----------|------------|
| **小説家になろう** | Selenium | ✅ 実装済み | Email/Password | 10 req/min |
| **カクヨム** | 非公式REST API | ✅ 実装済み | API Token | 30 req/min |
| **楽天Kobo** | 公式OAuth2 API | 🚧 実装済み/要審査 | Client ID/Secret | 60 req/min |
| **Kindle (KDP)** | 公式OAuth2 API | 🚧 実装済み/要審査 | Client ID/Secret/Refresh Token | 30 req/min |

> **注意**: KoboとKindleは公式API利用のため、それぞれのプラットフォームで開発者登録・審査が必要です。

#### セットアップ

`.env` に認証情報を設定：

```env
# 小説家になろう
NAROU_EMAIL=your_email@example.com
NAROU_PASSWORD=your_password

# カクヨム (マイページ > 設定 > API設定で取得)
KAKUYOMU_API_TOKEN=your_api_token
KAKUYOMU_USER_ID=your_user_id

# 楽天Kobo (開発者ポータルで取得)
KOBO_CLIENT_ID=your_client_id
KOBO_CLIENT_SECRET=your_client_secret

# Amazon KDP (LWA認証フローで取得)
KINDLE_CLIENT_ID=your_client_id
KINDLE_CLIENT_SECRET=your_client_secret
KINDLE_REFRESH_TOKEN=your_refresh_token
KINDLE_MARKETPLACE_ID=A1VC38T7YXB528  # 日本
```

#### API経由での投稿

**1. パイプライン実行時に投稿 (新規生成+投稿)**

```bash
curl -X POST http://localhost:8200/commercial/run \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "series_config": {
      "keywords": "ファンタジー,冒険",
      "target_eps": 10,
      "platforms": ["narou", "kakuyomu"]
    },
    "samples": [],
    "platforms": ["narou", "kakuyomu"],
    "do_publish": true
  }'
```

**2. 既存書籍の投稿**

```bash
curl -X POST http://localhost:8200/commercial/publish \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": 1,
    "platforms": ["narou", "kakuyomu"],
    "episode_range": [1, 5]
  }'
```

**3. 投稿ステータス確認**

```bash
curl -X POST http://localhost:8200/commercial/publish/status \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": 1,
    "platform": "kakuyomu",
    "post_id": "work_123"
  }'
```

**4. 投稿履歴取得**

```bash
curl -X GET http://localhost:8200/commercial/publish/records/1 \
  -H "Authorization: Bearer YOUR_API_KEY"
```

詳細な使い方は [docs/publishers.md](docs/publishers.md) を参照してください。

---

## 12. LLMプロバイダ設定 & ルーティング・拡張ガイド

### 12.1 サポートプロバイダと切り替え設定

AutoNovel は、主要な商用LLMプロバイダを標準サポートしています。環境変数 `LLM_PROVIDER` によってシームレスに切り替え可能です。

**実装済みプロバイダ (5種):**

| プロバイダ名 | `LLM_PROVIDER` 設定値 | 必要APIキー / エンドポイント | 特徴 |
| :--- | :--- | :--- | :--- |
| **OpenAI** | `openai` | `OPENAI_API_KEY` | GPT-4o, o1 による極めて高い文章力と構成力 |
| **Google Gemini** | `gemini` | `GEMINI_API_KEY` | 巨大コンテキストウィンドウ、高速推論 |
| **Anthropic Claude** | `claude` | `ANTHROPIC_API_KEY` | 論理的思考と長文一貫性に優れる |
| **Local LLM (Ollama)** | `ollama` | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | ローカル実行、プライバシー保護 |
| **vLLM** | `vllm` | `VLLM_BASE_URL`, `VLLM_MODEL` | 高性能ローカル推論サーバー |
| **Mock / Test** | `mock` | なし (自動フォールバック) | CI/テスト環境用の高速モック生成 |

### 12.2 プロバイダ別設定例

```bash
# OpenAI の場合
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o-mini

# Google Gemini の場合
LLM_PROVIDER=gemini
GEMINI_API_KEY=xxx
GEMINI_MODEL=gemini-1.5-flash

# Anthropic Claude の場合
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Ollama の場合 (ローカル)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# vLLM の場合 (ローカル推論サーバー)
LLM_PROVIDER=vllm
VLLM_BASE_URL=http://localhost:8000
VLLM_MODEL=meta-llama/Llama-3.1-8B-Instruct

# Mock (開発/テスト用)
LLM_PROVIDER=mock
```

> **注意**: 未知のプロバイダが指定された場合は WARNING ログが出力され `MockLLMAdapter` にフォールバックします。

---

### 12.2 プロバイダファクトリとアダプタアーキテクチャ

全てのLLMアダプタは抽象基底クラス `BaseLLMAdapter` を継承しており、アプリケーション全体はファクトリ `get_llm_adapter()` を通じて呼び出されます。

```python
# src/services/llm/base.py
from abc import ABC, abstractmethod

class BaseLLMAdapter(ABC):
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """テキスト生成を実行して文字列を返す。"""
        pass
```

### 12.3 カスタムLLMアダプタの実装例

自社ホスティングの推論サーバーや新しいLLMモデルを追加する場合の実装例です：

```python
# src/services/llm/custom_adapter.py
import os
import httpx
from src.services.llm.base import BaseLLMAdapter

class CustomVLLMAdapter(BaseLLMAdapter):
    def __init__(self, endpoint_url: str | None = None):
        self.endpoint_url = endpoint_url or os.getenv("VLLM_ENDPOINT", "http://localhost:8000/v1/completions")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        payload = {
            "prompt": f"{system_prompt}\n\nUser: {prompt}\n\nAssistant:",
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.endpoint_url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["text"].strip()
```

---

## 13. REST API 完全リファレンス

Base URL: `http://localhost:8200`（Nginx本番時: `http://localhost:8080`）
対話型API仕様書: `http://localhost:8200/docs` (Swagger UI) / `http://localhost:8200/redoc` (ReDoc)

### 13.1 主要エンドポイント一覧

| メソッド | パス | 説明 | 認証/制限 |
| :--- | :--- | :--- | :--- |
| `POST` | `/easy_mode/generate` | かんたんモード小説執筆タスク投入 | レート制限あり (10req/min) |
| `GET` | `/easy_mode/status/{task_id}` | 非同期タスクの進捗・結果取得 | なし |
| `DELETE` | `/easy_mode/task/{task_id}` | 実行中タスクのキャンセル | なし |
| `GET` | `/easy_mode/export/{book_id}` | 納品パッケージ (ZIP) ダウンロード | なし |
| `POST` | `/easy_mode/gacha` | 3案企画アイデアガチャ生成 | なし |
| `POST` | `/easy_mode/digest` | 前話テキストのダイジェスト要約作成 | なし |
| `POST` | `/easy_mode/promote` | かんたん作品のアドバンスド昇格 | なし |
| `GET` | `/graph/knowledge/{book_id}` | ナレッジグラフデータ (ノード/エッジ) 取得 | なし |
| `POST` | `/multimedia/generate` | 統合アセットパック生成 (README互換) | `ENABLE_MULTIMEDIA=true` 必須 |
| `POST` | `/multimedia/asset-pack` | 統合アセットパック生成 (標準) | `ENABLE_MULTIMEDIA=true` 必須 |
| `POST` | `/multimedia/media-mix` | メディアミックス台本生成 | `ENABLE_MULTIMEDIA=true` 必須 |
| `POST` | `/multimedia/if-routes` | IFルートグラフ生成 | `ENABLE_MULTIMEDIA=true` 必須 |
| `POST` | `/multimedia/ebook` | eBook エクスポート (EPUB/PDF/MOBI) | `ENABLE_MULTIMEDIA=true` 必須 |
| `GET` | `/multimedia/tasks/{id}` | マルチメディア生成タスクの進捗 | `ENABLE_MULTIMEDIA=true` |
| `GET` | `/multimedia/assets/{book_id}` | 作品別アセット一覧取得 | `ENABLE_MULTIMEDIA=true` |
| `POST` | `/api/export/ebook` | eBook エクスポート (README互換エイリアス) | `ENABLE_MULTIMEDIA=true` 必須 |
| `POST` | `/collab/versions` | 共同編集 ChapterVersion 保存 (CRDT) | なし |
| `GET` | `/collab/versions/{book_id}/{ep}` | 章のバージョン履歴取得 | なし |
| `GET` | `/health` | 総合多段ヘルスチェック (DB, Queue, Metrics) | なし |
| `GET` | `/metrics` | プロセス内メトリクススナップショット取得 | なし |

---

### 13.2 かんたんモード系 API

#### 1. `POST /easy_mode/generate`
- **Request Body (`EasyModeInput`)**:
  ```json
  {
    "chapter_history": ["第1話のあらすじテキスト..."],
    "current_chapter": "薄暗いダンジョンの中、少年アルトは古代の剣を抜いた。",
    "character_params": {
      "name": "アルト",
      "personality": "熱血・正義感が強い",
      "ability": "古代魔導剣術",
      "genre": "ハイファンタジー (R15)"
    },
    "content_length_limit": 2000
  }
  ```
- **Response (200 OK - `GenerationResponse`)**:
  ```json
  {
    "task_id": "c7a8b9e1-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
    "output": "",
    "completion_time_ms": 0,
    "error": "",
    "suggestions": [
      "生成タスク ID: c7a8b9e1-2f3a-4b5c-6d7e-8f9a0b1c2d3e を投入しました。"
    ]
  }
  ```

#### 2. `GET /easy_mode/status/{task_id}`
- **Response - 完了時 (200 OK)**:
  ```json
  {
    "task_id": "c7a8b9e1-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
    "status": "completed",
    "result": {
      "output": "抜かれた魔剣が青白く輝き、アルトの体に未知の魔力が流れ込む……。",
      "suggestions": [
        "ダンジョンの奥から響く咆哮と未知の魔物との遭遇",
        "魔剣に宿る古代の精霊との精神対話",
        "崩落する迷宮からの脱出劇"
      ],
      "completion_time_ms": 1420
    }
  }
  ```

#### 3. `GET /easy_mode/export/{book_id}`
- **Response (200 OK)**:
  - `Content-Type: application/zip`
  - `Content-Disposition: attachment; filename="export_1.zip"; filename*=UTF-8''export_1.zip`

---

### 13.3 ナレッジグラフ・挿絵・マーケティング系 API

#### 1. `GET /graph/knowledge/{book_id}`
- **Response (200 OK)**:
  ```json
  {
    "nodes": [
      {"id": "char_1", "label": "アルト", "type": "character", "role": "protagonist"},
      {"id": "char_2", "label": "エレナ", "type": "character", "role": "heroine"},
      {"id": "item_1", "label": "古代の魔剣", "type": "item", "rarity": "legendary"}
    ],
    "edges": [
      {"source": "char_1", "target": "char_2", "relation": "仲間・好意", "weight": 0.8},
      {"source": "char_1", "target": "item_1", "relation": "所有", "weight": 1.0}
    ]
  }
  ```

---

### 13.4 オブザーバビリティ系 API

#### 1. `GET /health`
```json
{
  "status": "ok",
  "components": {
    "database": {
      "status": "ok",
      "latency_ms": 1.15
    },
    "queue": {
      "status": "ok",
      "backend": "RedisHuey"
    }
  },
  "metrics": {
    "tasks_enqueued": 50,
    "tasks_completed": 48,
    "tasks_failed": 2,
    "exports_attempted": 20,
    "exports_succeeded": 20,
    "health_checks": 145
  }
}
```

#### 2. `GET /metrics`
```json
{
  "tasks_enqueued": 50,
  "tasks_completed": 48,
  "tasks_failed": 2,
  "exports_attempted": 20,
  "exports_succeeded": 20,
  "health_checks": 145
}
```

---

## 14. 設定パラメータ & 環境変数リファレンス

すべての設定は環境変数または `.env` ファイルで制御可能です。

| 環境変数名 | デフォルト値 | 必須 | 説明 |
| :--- | :--- | :---: | :--- |
| `DATABASE_URL` | `sqlite:///./autonovel.db` | - | データベース接続URL (`postgresql+psycopg2://...`) |
| `HUEY_BACKEND` | `sqlite` | - | タスクキュー種別 (`redis` または `sqlite`) |
| `REDIS_URL` | `redis://localhost:6379/0` | - | Redis接続文字列 (`HUEY_BACKEND=redis` 時に使用) |
| `LLM_PROVIDER` | `mock` (キー未設定時) | - | 使用する推論エンジン (`openai`, `gemini`, `mock`)。`claude`/`ollama` を直接指定すると ERROR ログ出力後 Mock にフォールバック。OpenAI 互換エンドポイント経由でアクセス可能。 |
| `OPENAI_API_KEY` | (なし) | 条件付 | OpenAI APIキー (`LLM_PROVIDER=openai` 時に必須) |
| `GEMINI_API_KEY` | (なし) | 条件付 | Google Gemini APIキー (`LLM_PROVIDER=gemini` 時に必須) |
| `ANTHROPIC_API_KEY` | (なし) | 条件付 | Anthropic APIキー (`LLM_PROVIDER=claude` 時に必須) |
| `ENABLE_GRAPHRAG` | `true` | - | AGE へのエンティティ反映・ハイブリッド検索の有効化 |
| `AGE_GRAPH_NAME` | `autonovel_graph` | - | Apache AGE グラフ名 |
| `AUTONOVEL_RAG_MODE` | `auto` | - | 検索バックエンドの選択 (`auto` / `chroma` / `pgvector` / `memory`) |
| `RAG_FALLBACK_MODE` | `memory` | - | ベクトルストア障害時のフォールバック |
| `RERANKER_BACKEND` | `simple` | - | リランカ実装 (`simple` / `cross-encoder` / `none`) |
| `CHROMA_HOST` / `CHROMA_PORT` | - | - | スタンドアロン ChromaDB を使用する場合の接続先 |
| `REQUIRE_PG` | `false` | - | 起動時に PostgreSQL 接続を必須化 |
| `REQUIRE_CHROMA` | `false` | - | 起動時に ChromaDB 接続を必須化 |
| `ENABLE_MULTIMEDIA` | `false` | - | `/multimedia/*` ルーターとマルチメディア生成を有効化 |
| `CORS_ORIGINS` | `http://localhost:5173,...` | - | 許可するオリジンのカンマ区切りホワイトリスト |
| `POSTGRES_PASSWORD` | (なし) | 本番 | 本番Docker構成におけるPostgreSQLパスワード |
| `REDIS_PASSWORD` | (なし) | 本番 | 本番Docker構成におけるRedis認証パスワード |
| `LOG_LEVEL` | `INFO` | - | ルートログレベル (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_FORMAT` | `json` | - | ログフォーマット (`json` または `text`) |
| `APP_ENV` | `local` | - | 実行環境識別子 (`local`, `staging`, `production`) |
| `UVICORN_WORKERS` | `2` | - | 本番 Uvicorn ワーカープロセス数 |

---

## 15. セキュリティ & 堅牢性設計

AutoNovel は、公開環境および商用運用に耐えうる多層防御セキュリティを実装しています。

1. **IP単位スライディングウィンドウ・レートリミッター (`src/backend/rate_limit.py`)**:
   `/easy_mode/generate` 等の重いエンドポイントに対し、同一IPからの短時間過剰リクエストを自動遮断 (HTTP 429 Too Many Requests)。
2. **厳格なホワイトリスト型 CORS 制御 (`src/backend/server.py`)**:
   環境変数 `CORS_ORIGINS` に明示されたドメインからのみリクエストを許可。ワイルドカード (`*`) による不用意な全開放を防止。
3. **Pydantic v2 スキーマバリデーション**:
   すべての入力パラメータに対して厳格な型・文字数上限・負数禁止ルールを適用し、インジェクション攻撃やメモリ枯渇を防止。
4. **本番パスワード未設定の強制起動防止 (`docker-compose.prod.yml`)**:
   本番コンテナ起動時、`POSTGRES_PASSWORD` または `REDIS_PASSWORD` が空の場合は安全のためコンテナが即座に起動を停止。
5. **リトライ & サーキットブレーカー (`src/services/retry_decorator.py`)**:
   外部LLM APIの一時的な障害（HTTP 500, 503, 429）に対し、指数バックオフ付き自動リトライを実行。

---

## 16. オブザーバビリティ (ロギング・ヘルス・メトリクス)

### 16.1 構造化 JSON ロギング (`src/backend/logging_config.py`)

標準設定で JSON 形式の構造化ログを出力し、Datadog、CloudWatch、Elasticsearch、Loki などのログ収集基盤にそのまま取り込み可能です。

```json
{
  "timestamp": "2026-09-01T12:00:00.123456",
  "level": "INFO",
  "logger": "src.backend.routers.easy_mode",
  "message": "Enqueued generation task: task_id=c7a8b9e1-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
  "app": "autonovel",
  "version": "0.2.0",
  "env": "production"
}
```

### 16.2 統合ヘルスチェック & メトリクス

- **`/health` エンドポイント**:
  データベースへの ping (`SELECT 1`) による疎通性・応答レイテンシ、および Huey キューブローカーの稼働状況を同時に検証。
- **`/metrics` エンドポイント**:
  タスク投入数、完了数、失敗数、エクスポート成功数、ヘルスチェック呼出数を軽量インメモリカウンタでリアルタイム追跡。

---

## 17. 本番デプロイ & インフラ運用設計

### 17.1 Nginx リバースプロキシ構成

本番環境（`docker-compose.prod.yml`）では、フロントエンドに Nginx を配置します：
- 静的ファイル（HTML, JS, CSS, 画像）は Nginx が直接高速配信（gzip/brotli圧縮有効）。
- `/easy_mode/*`, `/graph/*`, `/health`, `/metrics` のみ内部の FastAPI サーバー (Uvicorn) へ転送。
- クライアントの生IPアドレスを `X-Forwarded-For` ヘッダーで安全にバックエンドへ伝達。

### 17.2 データベースマイグレーション (Alembic)

スキーマ変更は Alembic を用いて安全にマイグレーションされます：

```bash
# 新しいマイグレーションスクリプトの自動生成
alembic revision --autogenerate -m "Add new plot column"

# マイグレーションの適用
alembic upgrade head

# ロールバック
alembic downgrade -1
```

> ⚠️ **マイグレーションファイルの配置**: `alembic.ini` の `script_location = src/backend/alembic` に従い、マイグレーションファイルは **`src/backend/alembic/versions/`** に配置されています（`0000_initial_migration` 〜 `0013_graph_pipeline_idempotency`）。カスタムマイグレーションを追加する際は `src/backend/alembic/versions/` に置いてください。

---

## 18. テスト戦略 & 品質ゲート

AutoNovel は、堅牢なソフトウェア品質を担保するため、複数レイヤーの自動テストと静的解析ゲートを配備しています。

```mermaid
graph LR
    subgraph "品質ゲート 1: 静的解析"
        Ruff["Ruff (Lint & Format)"]
        Mypy["Mypy (Type Check)"]
        ESLint["ESLint & TSC (Frontend)"]
    end

    subgraph "品質ゲート 2: 自動テスト"
        Pytest["pytest (Backend Unit/Integration)"]
        Vitest["Vitest (Frontend RTL/MSW)"]
    end

    subgraph "品質ゲート 3: 結合 & スキーマ検証"
        OpenAPI["OpenAPI 差分検知"]
        Smoke["PowerShell スモークテスト"]
    end

    Ruff --> Pytest
    Mypy --> Pytest
    ESLint --> Vitest
    Pytest --> OpenAPI
    Vitest --> OpenAPI
    OpenAPI --> Smoke
```

### テスト実行コマンド集

```bash
# 1. バックエンド全テストの実行 (pytest, 80% カバレッジゲート)
py -m pytest -q --tb=short --cov=src --cov-fail-under=80

# 2. Python 静的解析 (Ruff)
py -m ruff check src tests

# 3. Python 型検査 (Mypy, 警告のみ)
py -m mypy src

# 4. フロントエンド単体・統合テスト (Vitest + MSW)
cd frontend && npm run test:ci -- --coverage

# 5. フロントエンド Lint & 型検査
cd frontend && npm run lint && npm run typecheck

# 6. 全品質ゲートの一括検証 (コミット・PR前必須)
make verify

# 7. 稼働中サーバーに対する E2E スモークテスト
./scripts/smoke_test.ps1
```

---

## 19. トラブルシューティング & FAQ

### Q1: フロントエンドで「生成リクエストに失敗しました」または HTTP 429 が返る
- **原因**: 短時間に連続して執筆ボタンを押したため、IP単位のレートリミッターに抵触した可能性があります。
- **対処法**: 60秒待機してから再試行してください。開発環境で緩和したい場合は `src/backend/rate_limit.py` の `max_requests` を調整してください。

### Q2: 進行バーが `pending` のまま完了しない
- **原因**: Huey ワーカープロセスが起動していないか、タスクキューのバックエンド設定 (`HUEY_BACKEND`) が API とワーカーで異なっています。
- **対処法**:
  - ローカル実行時: ターミナルで `py -m huey.bin.huey_consumer src.backend.tasks.huey.huey` が稼働しているか確認してください。
  - Docker 実行時: `docker compose ps` で `autonovel_worker` コンテナが `Up` 状態か確認してください。

### Q3: 本番 Docker Compose の起動時にコンテナが即座に終了する
- **原因**: `.env` ファイルに `POSTGRES_PASSWORD` または `REDIS_PASSWORD` が設定されていません。
- **対処法**: `.env.example` をコピーして `.env` を作成し、強固なパスワードを設定してください。

### Q4: 実際のLLM（OpenAI/Gemini等）で執筆したい
- **対処法**: `.env` ファイルに `LLM_PROVIDER=openai` および `OPENAI_API_KEY=sk-...` を設定し、サーバーおよびワーカーを再起動してください。

---

## 20. 開発ワークフロー & コントリビューション

開発における一般的なタスクは `Makefile` に集約されています。

```bash
make help          # 利用可能なコマンド一覧を表示
make install       # バックエンドの依存ライブラリをインストール
make dev           # バックエンド・フロントエンドの全環境セットアップ
make test          # バックエンド pytest を実行
make lint          # Ruff による静的コード解析
make typecheck     # Mypy による型検査
make openapi       # docs/openapi.json を再生成
make frontend-test # フロントエンド Vitest を実行
make frontend-lint # フロントエンド ESLint + 型検査を実行
make verify        # 全品質ゲートを一括実行 (PR前必須)
make clean         # キャッシュや一時DBファイルをクリーンアップ
```

コントリビューションの詳細は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。
品質計画・テスト網羅率プランは [TEST_COVERAGE_PLAN.md](TEST_COVERAGE_PLAN.md) を、パイプライン統合の将来計画は [PIPELINE_UNIFICATION_PLAN.md](PIPELINE_UNIFICATION_PLAN.md) / [UNIFIED_PIPELINE_IMPLEMENTATION_PLAN.md](UNIFIED_PIPELINE_IMPLEMENTATION_PLAN.md) を参照してください。

> **現行バージョン**: v4.0.0 (`pyproject.toml`, `frontend/package.json`, Docker イメージ `autonovel-backend:4.0.0` / `autonovel-frontend:4.0.0`)。直近のリリースノートは [CHANGELOG.md](CHANGELOG.md)。

---

## 21. ロードマップ & ライセンス

### 21.1 今後のロードマップ
- [x] **eBook エクスポート (EPUB 3)**: 縦書き・ルビ・目次対応 (v4.0 で実装済み)
- [x] **マルチメディア生成 (Phase 7)**: シーン画像 / 立ち絵 / 表紙 / ボイス / BGM パック (v4.0 で実装済み)
- [x] **共同編集 (CRDT)**: `ChapterVersion` ベクタークロックマージ (v4.0 で実装済み)
- [x] **GraphRAG 高度化**: pgvector / ChromaDB / BM25 / cross-encoder rerank の RRF 統合 (v4.0 で実装済み)
- [ ] **リアルタイム音声対話ブレインストーミング**: 音声認識/音声合成によるAIプロット会議機能。
- [ ] **多言語自動ローカライズ**: 生成された日本語小説の英語・中国語圏向け高品質翻訳パイプライン。
- [ ] **Web投稿サイト API 連携**: 小説家になろう・カクヨム等への自動下書き投稿機能。

### 21.2 ライセンス & クレジット

本プロジェクトは [MIT License](LICENSE) の下で公開されています。商用利用・改変・再配布が自由に認められています。

---

<div align="center">
  <sub>Built with ❤️ for Novelists, Creators, and AI Engineers Worldwide.</sub>
</div>
