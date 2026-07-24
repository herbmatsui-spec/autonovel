# リポジトリ環境衛生リファクタリング実装計画書

## 目的

リポジトリ・ルート階層（autonovel/ 直下）に散乱する一時ファイル・ログ・DBファイルを整理し、`.gitignore` と専用フォルダへの集約を実現する。

---

## 対象ファイル一覧

### A. 削除対象（一時ファイル・スクリプト）
| # | ファイル名 | 種類 |
|---|-----------|------|
| 1 | `=1.5.0` | 不明ファイル（等号始まり） |
| 2 | `$null` | 不明ファイル（Windows 予約名） |
| 3 | `tmp_replace_normalize.py` | デバッグ用スクリプト |
| 4 | `balance_run.log` | 実行ログ |
| 5 | `integration_test_results.log` | テスト結果ログ |
| 6 | `files.zip` | アーカイブ |
| 7 | `balance_verify_result.json` | 結果JSON |
| 8 | `generated_sample_novel.md` |  генераated生成物 |
| 9 | `server.log` | サーバーログ |
| 10 | `autonovel2` | 不明ファイル |

### B. 移動対象（DBファイル → storage/db/）
| # | ファイル名 | 備考 |
|---|-----------|------|
| 11 | `kaku_hegemony_v2.db` | メインDB |
| 12 | `kaku_hegemony_v2.db-shm` | WAL |
| 13 | `kaku_hegemony_v2.db-wal` | WAL |
| 14 | `kaku_hegemony_v2_huey.db-shm` | Huey用 |
| 15 | `kaku_hegemony_v2_huey.db-wal` | Huey用 |
| 16 | `huey.db` | Huey DB |
| 17 | `demo_hegemony.db-shm` | デモ用 |
| 18 | `demo_hegemony.db-wal` | デモ用 |

### C. .gitignore 修正対象
| # | 追加パターン | 理由 |
|---|------------|------|
| 19 | `*.log` | ログファイル一括除外 |
| 20 | `*.zip` | アーカイブ除外 |
| 21 | `*.json`（ルート） | 結果JSON除外（`config/`は保持） |
| 22 | `autonovel2` | 不明ファイル除外 |
| 23 | `=*` | 等号始まりファイル除外 |
| 24 | `$null` | Windows予約名ファイル除外 |

---

## 24ステップ実装手順

### Phase 1: 事前準備（Step 1-3）

**Step 1** — 作業前に現在の git 状態を確認する
```bash
cd autonovel
git status --short
git log --oneline -5
```
**目的**: 変更前後の差分比較用baseline記録

**Step 2** — `storage/db/` ディレクトリを作成する
```bash
mkdir -p storage/db
```
**目的**: DBファイルの集約先を確保（既存の `storage/` に追加）

**Step 3** — 現在の `.gitignore` をバックアップする
```bash
cp .gitignore .gitignore.backup
```
**目的**: 手順誤り時に即座に復元可能

---

### Phase 2: DBファイル移動（Step 4-10）

**Step 4** — `kaku_hegemony_v2.db` を `storage/db/` に移動する
```bash
mv kaku_hegemony_v2.db storage/db/
```
**目的**: メインSQLite DBを専用フォルダへ集約

**Step 5** — `kaku_hegemony_v2.db-shm` と `kaku_hegemony_v2.db-wal` を `storage/db/` に移動する
```bash
mv kaku_hegemony_v2.db-shm storage/db/
mv kaku_hegemony_v2.db-wal storage/db/
```
**目的**: 同一DBのWAL/SHMファイルを共に移動（分離禁止）

**Step 6** — `huey.db` を `storage/db/` に移動する
```bash
mv huey.db storage/db/
```
**目的**: Hueyタスクキュー用DBを専用フォルダへ集約

**Step 7** — `kaku_hegemony_v2_huey.db-shm` と `kaku_hegemony_v2_huey.db-wal` を `storage/db/` に移動する
```bash
mv kaku_hegemony_v2_huey.db-shm storage/db/
mv kaku_hegemony_v2_huey.db-wal storage/db/
```
**目的**: Huey関連DBのWAL/SHMを共に移動

**Step 8** — `demo_hegemony.db-shm` と `demo_hegemony.db-wal` を `storage/db/` に移動する
```bash
mv demo_hegemony.db-shm storage/db/
mv demo_hegemony.db-wal storage/db/
```
**目的**: デモ用DBのWAL/SHMを共に移動

**Step 9** — 移動完了後、DB接続設定のpathsを確認する
```bash
grep -r "kaku_hegemony_v2.db" --include="*.py" --include="*.toml" --include="*.ini" --include="*.env*" -l
```
**目的**: アプリがDBパスをハードコードしていないか確認（見つかった場合は Step 10 で修正）

**Step 10** — DBパスがハードコードされている場合、`storage/db/` を参照するよう修正する
```python
# 修正例（見つかったファイルに応じて）
DB_PATH = "storage/db/kaku_hegemony_v2.db"
```
**目的**: 移動後のアプリ動作 보장（相対パスで `storage/db/` 即可参照なら不要）

---

### Phase 3: 一時ファイル削除（Step 11-18）

**Step 11** — `=1.5.0` を削除する
```bash
rm "=1.5.0"
```
**目的**: 等号始まり文件名（コマンドラインで誤動作の原因）

**Step 12** — `$null` を削除する
```bash
rm "\$null"
```
**目的**: Windows 予約デバイス名（ファイル名として不正常）

**Step 13** — `tmp_replace_normalize.py` を削除する
```bash
rm tmp_replace_normalize.py
```
**目的**: デバッグ用スクリプトの散乱防止

**Step 14** — `balance_run.log` と `integration_test_results.log` を削除する
```bash
rm balance_run.log
rm integration_test_results.log
```
**目的**: 実行ログの一元管理（`logs/` 目录下に残す方針が好ましいが残りが確認できないため削除）

**Step 15** — `files.zip` を削除する
```bash
rm files.zip
```
**目的**: アーカイブファイルの散乱防止

**Step 16** — `balance_verify_result.json` を削除する
```bash
rm balance_verify_result.json
```
**目的**: 結果JSONは git 管理不要

**Step 17** — `server.log` を削除する
```bash
rm server.log
```
**目的**: サーバーログの散乱防止

**Step 18** — `generated_sample_novel.md` を削除する
```bash
rm generated_sample_novel.md
```
**目的**:  генераated生成物は git 管理不要

---

### Phase 4: 不明ファイルの処理（Step 19-20）

**Step 19** — `autonovel2` ファイルを調査し、内容を精査する
```bash
file autonovel2   # ファイル種別の確認
cat autonovel2    # 中身がコードか設定か確認
```
**目的**: 0バイト空文件的か実体があるか判定

**Step 20** — 调查结果に基づき `autonovel2` を削除または正規配置する
```bash
# 空ファイルまたは不要と判断した場合
rm autonovel2
# 必要に応じてリネーム・配置変更
# mv autonovel2 storage/archives/
```
**目的**: 正体不明ファイルの散乱防止

---

### Phase 5: .gitignore 更新（Step 21-23）

**Step 21** — `.gitignore.backup` を `.gitignore` に復元する（元に戻す）
```bash
cp .gitignore.backup .gitignore
```
**目的**: 現在の .gitignore をベースとして Step 22 で追加するため

**Step 22** — `.gitignore` に以下の行を追加する（計6パターン）
```
# === Repository Hygiene: 散乱ファイル除外 ===
# ログファイル
*.log
# アーカイブ
*.zip
# 結果JSON（config/ 配下は手動で除外しない）
# 注意: config/*.json は保持したい場合は !config/*.json を追加
# ルート直下の JSON ファイル
/*.json
# 不明ファイル
autonovel2
# 等号始まりファイル
=*
# Windows 予約名ファイル
$null
```
**目的**: 既存ルールと重複しない新規ルールを追加

**Step 23** — `.gitignore` から冗長ルールを整理する（既存だが時代遅れの行を削除）
```bash
# 以下が `.gitignore` に重複・不要として存在すれば削除:
# - 既に storage/ に集約されたファイル群の個別指定
# - tmp_replace_normalize.py（既に削除済みなので不要に）
# - start_app.bat（既にignore済み維持）
```
**目的**: `.gitignore` の可読性・保守性改善

---

### Phase 6: 検証（Step 24）

**Step 24** — リファクタリング完了後の検証を実行する
```bash
# 1) git status で散乱ファイルが消失したか確認
git status --short

# 2) storage/db/ にDBファイルが正しく配置されたか確認
ls -la storage/db/

# 3) .gitignore が意図通りに機能しているか確認
git check-ignore -v =1.5.0       # 出力がれば ignore 対象
git check-ignore -v balance_run.log
git check-ignore -v huey.db

# 4) アプリ動作確認（可能であれば）
# python -c "import sqlite3; sqlite3.connect('storage/db/kaku_hegemony_v2.db')"
```
**目的**: 移動・削除・ignore登録が全て正常に完了したか検証

---

## 想定成果物

| 項目 | 実施前 | 実施後 |
|------|--------|--------|
| ルート散乱ファイル数 | ~18ファイル | 0ファイル |
| DBファイルの配置 | `autonovel/` 直下 | `storage/db/` 集約 |
| .gitignore ログ除外 | 未反映（手動） | `*.log`  Glob パターン |
| 一時スクリプト | 残存 | 全削除 |

## 注意事項

- **Step 9-10**（DBパス参照確認）は実際のアプリコードの書き方によって不要の場合あり
- `storage/` ディレクトリは `.gitignore` ですで除外済みなので、DBファイルは git 管理外のまま
- `.coverage` は削除対象として記載がなかったため維持（テストカバレッジ）
- `run_all.bat`, `run_app.bat` はコミット対象_scriptsのため維持