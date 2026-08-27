# ContinuityTracker 拡張 実装計画書（低性能 LLM でも実装可能な 72 ステップ版）

## 0. 概要

本ドキュメントは、`novel_50ep` プロジェクト内の `ContinuityTracker` が「官能シーンのみ」に対応している課題（アーカイブ区分 10）を解消し、戦闘・会話・探索などの非官能シーンにも連続性チェックを拡張するための詳細実装計画である。

目標は次のとおり。

1. あらゆるシーン種別を統一的に扱える `SceneBase` モデルを導入する。
2. 宣言的ルール（YAML/JSON）で継続性を定義し、既存の `polish_tool` / `generator` / `score_reviewer` / `batch_runner` / `foreshadow_manager` と連携する。
3. 低性能な LLM でも 1 ステップずつ確実に実装できるよう、作業を 72 の小ステップに分割する。

各ステップは「対象ファイル」「目的」「作業内容」「受入基準」の 4 項目で構成し、必要に応じて最小限のコード例を示す。

---

## Phase 0：準備・調査（ステップ 1〜6）

### ステップ 1
- 対象ファイル：`novel_50ep/`（全体）
- 目的：現状の `ContinuityTracker` の所在を特定する。
- 作業内容：`grep -rn "ContinuityTracker"` を実行し、該当ファイル名と行数をメモする。まだ存在しない場合は「新規作成」と記録する。
- 受入基準：対象ファイル一覧が `TODO` メモに記載されている。

### ステップ 2
- 対象ファイル：`novel_50ep/generator.py`
- 目的：シーン生成フローを把握する。
- 作業内容：`generator.py` を読み、シーン単位でどの関数が呼ばれ、どのような辞書/オブジェクトが返るかを 10 行程度のメモにまとめる。
- 受入基準：生成関数名と戻り値の形がメモにある。

### ステップ 3
- 対象ファイル：`novel_50ep/foreshadow_manager.py`
- 目的：伏線管理がどのデータ構造で情報を持つか確認する。
- 作業内容：`foreshadow_manager.py` の `register` / `get` 系関数を読み、フィールド名（例：`id`, `type`, `text`）をメモする。
- 受入基準：伏線オブジェクトのフィールド一覧がメモにある。

### ステップ 4
- 対象ファイル：`novel_50ep/polish_tool.py`
- 目的：校正ツールのフックポイントを探す。
- 作業内容：`polish_tool.py` で「生成テキストを受け取って返す」関数を 1 つ特定し、関数名をメモする。
- 受入基準：フック候補関数名がメモにある。

### ステップ 5
- 対象ファイル：`novel_50ep/score_reviewer.py`
- 目的：評価スコア計算の拡張点を探す。
- 作業内容：`score_reviewer.py` の `score` 計算関数を読み、「ここにペナルティを加算できる」場所を 1 箇所マークする。
- 受入基準：スコア加算予定箇所にコメント `# CONTINUITY_HOOK` を置いた。

### ステップ 6
- 対象ファイル：`novel_50ep/tests/test_novel_50ep.py`
- 目的：テストの書き方にならう。
- 作業内容：既存テストの `def test_*` を 1 つ読み、アサートの書き方をコピーして `test_continuity_dummy.py` を新規作成し、必ず通る `assert True` だけのテストを書く。
- 受入基準：`pytest novel_50ep/tests/test_continuity_dummy.py` が緑になる。

---

## Phase 1：統一シーン基底クラスとシリアライズ（ステップ 7〜15）

### ステップ 7
- 対象ファイル：`novel_50ep/scene_model.py`（新規）
- 目的：全シーンの基底クラスを作る。
- 作業内容：以下のみを定義する。
```python
class SceneBase:
    def __init__(self, id: str, type: str, start: int, end: int):
        self.id = id
        self.type = type
        self.start = start
        self.end = end
```
- 受入基準：ファイルが ImportError なく読み込める。

### ステップ 8
- 対象ファイル：`novel_50ep/scene_model.py`
- 目的：`to_dict` を追加し、JSON 化できるようにする。
- 作業内容：`SceneBase` に `def to_dict(self): return {"id": self.id, "type": self.type, "start": self.start, "end": self.end}` を追加。
- 受入基準：`SceneBase("s1","erotic",0,10).to_dict()` が辞書を返す。

### ステップ 9
- 対象ファイル：`novel_50ep/scene_model.py`
- 目的：官能シーン専用クラスを作る。
- 作業内容：
```python
class EroticScene(SceneBase):
    def __init__(self, id, start, end, characters=None):
        super().__init__(id, "erotic", start, end)
        self.characters = characters or []
```
- 受入基準：サブクラスがインスタンス化できる。

### ステップ 10
- 対象ファイル：`novel_50ep/scene_model.py`
- 目的：会話シーンの雛形を作る。
- 作業内容：
```python
class DialogueScene(SceneBase):
    def __init__(self, id, start, end, speakers=None, utterances=None):
        super().__init__(id, "dialogue", start, end)
        self.speakers = speakers or []
        self.utterances = utterances or []
```
- 受入基準：インスタンス化できる。

### ステップ 11
- 対象ファイル：`novel_50ep/scene_model.py`
- 目的：戦闘シーンの雛形を作る。
- 作業内容：
```python
class CombatScene(SceneBase):
    def __init__(self, id, start, end, hp=0, mp=0, equipment=None, enemies=None):
        super().__init__(id, "combat", start, end)
        self.hp = hp
        self.mp = mp
        self.equipment = equipment or []
        self.enemies = enemies or []
```
- 受入基準：インスタンス化できる。

### ステップ 12
- 対象ファイル：`novel_50ep/scene_model.py`
- 目的：探索シーンの雛形を作る。
- 作業内容：
```python
class ExplorationScene(SceneBase):
    def __init__(self, id, start, end, location="", items=None, map_flags=None):
        super().__init__(id, "exploration", start, end)
        self.location = location
        self.items = items or []
        self.map_flags = map_flags or {}
```
- 受入基準：インスタンス化できる。

### ステップ 13
- 対象ファイル：`novel_50ep/scene_model.py`
- 目的：ファクトリ関数で種別から生成できるようにする。
- 作業内容：
```python
def make_scene(type, **kw):
    table = {"erotic": EroticScene, "dialogue": DialogueScene,
             "combat": CombatScene, "exploration": ExplorationScene}
    return table[type](**kw)
```
- 受入基準：`make_scene("combat", id="c1", start=0, end=5)` が `CombatScene` を返す。

### ステップ 14
- 対象ファイル：`novel_50ep/scene_model.py`
- 目的：JSON から復元できる `from_dict` を追加。
- 作業内容：`SceneBase.from_dict(d)` をクラスメソッドとして追加し、`make_scene` を内部で使う。
- 受入基準：`SceneBase.from_dict({"type":"combat","id":"c1","start":0,"end":1,"hp":10})` が正しい属性を持つ。

### ステップ 15
- 対象ファイル：`novel_50ep/tests/test_scene_model.py`（新規）
- 目的：Phase 1 の動作を固定する。
- 作業内容：各クラスの `to_dict` / `from_dict` ラウンドトリップを `assert` するテストを書く。
- 受入基準：`pytest novel_50ep/tests/test_scene_model.py` が全て通る。

---

## Phase 2：宣言的ルールエンジン基盤（ステップ 16〜24）

### ステップ 16
- 対象ファイル：`novel_50ep/continuity_rules/`（新規ディレクトリ）
- 目的：ルール定義を格納する場所を作る。
- 作業内容：ディレクトリを作成し、空の `__init__.py` を置く。
- 受入基準：`import continuity_rules` がエラーにならない。

### ステップ 17
- 対象ファイル：`novel_50ep/continuity_rules/base.yaml`（新規）
- 目的：ルール記述フォーマットを決める。
- 作業内容：以下を書く。
```yaml
version: 1
rules: []
```
- 受入基準：YAML が `yaml.safe_load` で読める。

### ステップ 18
- 対象ファイル：`novel_50ep/rule_engine.py`（新規）
- 目的：ルールローダーを作る。
- 作業内容：
```python
import yaml, glob, os
def load_rules(dir_path):
    rules = []
    for f in glob.glob(os.path.join(dir_path, "*.yaml")):
        data = yaml.safe_load(open(f, encoding="utf-8"))
        rules.extend(data.get("rules", []))
    return rules
```
- 受入基準：`load_rules("novel_50ep/continuity_rules")` がリストを返す。

### ステップ 19
- 対象ファイル：`novel_50ep/rule_engine.py`
- 目的：単一ルール評価の枠組みを作る。
- 作業内容：関数 `def eval_rule(rule, prev, cur): return []` を追加（いったん空で OK）。
- 受入基準：関数が呼べる。

### ステップ 20
- 対象ファイル：`novel_50ep/rule_engine.py`
- 目的：ルール種別 `equals` を実装する。
- 作業内容：`eval_rule` 内で `if rule["op"]=="equals":` なら `prev[rule["field"]]==cur[rule["field"]]` を評価し、不一致なら違反辞書を返す。
- 受入基準：`equals` ルールで不一致が検出される。

### ステップ 21
- 対象ファイル：`novel_50ep/rule_engine.py`
- 目的：ルール種別 `subset` を実装する。
- 作業内容：`op=="subset"` で `set(cur[field]) <= set(prev[field])` を評価（戦闘装備の消失検出用）。
- 受入基準：装備が減った場合に違反が出る。

### ステップ 22
- 対象ファイル：`novel_50ep/rule_engine.py`
- 目的：ルール種別 `no_increase` を実装する。
- 作業内容：`op=="no_increase"` で `cur[field] <= prev[field]` を評価（HP の不自然な増加検出用）。
- 受入基準：HP が増えた場合に違反が出る。

### ステップ 23
- 対象ファイル：`novel_50ep/rule_engine.py`
- 目的：全ルールを回す `check_scenes(prev, cur, rules)` を作る。
- 作業内容：`for rule in rules: violations += eval_rule(rule, prev, cur)` をまとめる。
- 受入基準：`check_scenes` が違反リストを返す。

### ステップ 24
- 対象ファイル：`novel_50ep/tests/test_rule_engine.py`（新規）
- 目的：Phase 2 を固定する。
- 作業内容：`equals` / `subset` / `no_increase` の各パターンでテストを書く。
- 受入基準：`pytest` が全て通る。

---

## Phase 3：インクリメンタルチェック（ステップ 25〜32）

### ステップ 25
- 対象ファイル：`novel_50ep/continuity_tracker.py`（新規）
- 目的：トラッカーの骨組みを作る。
- 作業内容：
```python
class ContinuityTracker:
    def __init__(self, rules_dir):
        self.rules = load_rules(rules_dir)
        self.prev = None
```
- 受入基準：インスタンス化できる。

### ステップ 26
- 対象ファイル：`novel_50ep/continuity_tracker.py`
- 目的：`feed` メソッドで 1 シーンずつ受け取る。
- 作業内容：
```python
def feed(self, scene):
    v = []
    if self.prev:
        v = check_scenes(self.prev.to_dict(), scene.to_dict(), self.rules)
    self.prev = scene
    return v
```
- 受入基準：`feed` が初回は空、2 回目以降はチェック結果を返す。

### ステップ 27
- 対象ファイル：`novel_50ep/continuity_tracker.py`
- 目的：違反を蓄積できるようにする。
- 作業内容：`self.violations = []` を init に追加し、`feed` で `self.violations.extend(v)` する。
- 受入基準：`feed` 後 `tracker.violations` に履歴が残る。

### ステップ 28
- 対象ファイル：`novel_50ep/continuity_tracker.py`
- 目的：リセット機能を追加。
- 作業内容：`def reset(self): self.prev=None; self.violations=[]` を追加。
- 受入基準：`reset` で状態が空になる。

### ステップ 29
- 対象ファイル：`novel_50ep/continuity_tracker.py`
- 目的：シリアライズ（保存）機能を追加。
- 作業内容：`def save(self, path): json.dump([v for v in self.violations], open(path,"w"))` を追加。
- 受入基準：`save` で JSON ファイルが出力される。

### ステップ 30
- 対象ファイル：`novel_50ep/continuity_tracker.py`
- 目的：レポート文字列生成を追加。
- 作業内容：`def report(self): return "\n".join(f"{v['field']}: {v['msg']}" for v in self.violations)` を追加。
- 受入基準：`report` が人間可読な文字列を返す。

### ステップ 31
- 対象ファイル：`novel_50ep/continuity_rules/base.yaml`
- 目的：ダミールールを 1 つ書く。
- 作業内容：`rules:` に `{"type":"erotic","op":"equals","field":"characters","msg":"キャラ不一致"}` を追加。
- 受入基準：`load_rules` でルールが 1 件読める。

### ステップ 32
- 対象ファイル：`novel_50ep/tests/test_tracker_basic.py`（新規）
- 目的：Phase 3 を固定する。
- 作業内容：2 つの `EroticScene` を `feed` し、キャラ不一致で違反が出ることを `assert`。
- 受入基準：`pytest` が通る。

---

## Phase 4：会話シーンのルール（ステップ 33〜40）

### ステップ 33
- 対象ファイル：`novel_50ep/continuity_rules/dialogue.yaml`（新規）
- 目的：会話用ルールファイルを作る。
- 作業内容：`version:1` と空 `rules: []` だけ書く。
- 受入基準：YAML が読める。

### ステップ 34
- 対象ファイル：`novel_50ep/continuity_rules/dialogue.yaml`
- 目的：話者一致性ルールを追加。
- 作業内容：`op: subset`, `field: speakers`, `msg: "前シーンにいない話者が登場"` を追加（`type: dialogue` 限定）。
- 受入基準：新話者が出たとき違反になる。

### ステップ 35
- 対象ファイル：`novel_50ep/rule_engine.py`
- 目的：ルールに `type` 制限を実装。
- 作業内容：`eval_rule` の先頭で `if "type" in rule and rule["type"] != cur["type"]: return []` を追加。
- 受入基準：型が違うシーンではルールが適用されない。

### ステップ 36
- 対象ファイル：`novel_50ep/continuity_rules/dialogue.yaml`
- 目的：トピック継続ルールを追加。
- 作業内容：`op: equals`, `field: topics`, `msg: "トピックがリセットされている"` を追加。
- 受入基準：トピックが変わると違反になる。

### ステップ 37
- 対象ファイル：`novel_50ep/scene_model.py`
- 目的：`DialogueScene` に `topics` フィールドを追加。
- 作業内容：`self.topics = kw.get("topics", [])` を追加し、`to_dict` に含める。
- 受入基準：ラウンドトリップで `topics` が保存される。

### ステップ 38
- 対象ファイル：`novel_50ep/tests/test_dialogue_rules.py`（新規）
- 目的：会話ルールを固定。
- 作業内容：`speakers` が増えた場合と `topics` が変わった場合の 2 テストを書く。
- 受入基準：`pytest` が通る。

### ステップ 39
- 対象ファイル：`novel_50ep/generator.py`
- 目的：生成時に `DialogueScene` を作るフックを追加。
- 作業内容：会話生成後に `make_scene("dialogue", id=..., start=..., end=..., speakers=..., topics=...)` を返すよう既存関数の戻り値を拡張（後段互換のためタプルで返しても可）。
- 受入基準：generator がシーンオブジェクトを返せる。

### ステップ 40
- 対象ファイル：`novel_50ep/tests/test_generator_dialogue.py`（新規）
- 目的：generator と tracker の結合テスト。
- 作業内容：generator が返した `DialogueScene` を `tracker.feed` し、違反が正しく検出されることを `assert`。
- 受入基準：`pytest` が通る。

---

## Phase 5：戦闘シーンのルール（ステップ 41〜48）

### ステップ 41
- 対象ファイル：`novel_50ep/continuity_rules/combat.yaml`（新規）
- 目的：戦闘用ルールファイルを作る。
- 作業内容：`version:1` と空 `rules` を書く。
- 受入基準：読める。

### ステップ 42
- 対象ファイル：`novel_50ep/continuity_rules/combat.yaml`
- 目的：装備 `subset` ルール。
- 作業内容：`type: combat`, `op: subset`, `field: equipment`, `msg: "装備が消失"` を追加。
- 受入基準：装備が減ると違反。

### ステップ 43
- 対象ファイル：`novel_50ep/continuity_rules/combat.yaml`
- 目的：HP `no_increase` ルール。
- 作業内容：`type: combat`, `op: no_increase`, `field: hp`, `msg: "HPが回復行為なしで増加"` を追加。
- 受入基準：HP 増加で違反。

### ステップ 44
- 対象ファイル：`novel_50ep/continuity_rules/combat.yaml`
- 目的：MP `no_increase` ルール。
- 作業内容：HP と同様に `mp` でも追加。
- 受入基準：MP 増加で違反。

### ステップ 45
- 対象ファイル：`novel_50ep/rule_engine.py`
- 目的：数値比較で `None` 安全にする。
- 作業内容：`no_increase` 評価前に `if prev.get(field) is None or cur.get(field) is None: return []` を入れる。
- 受入基準：欠損値でクラッシュしない。

### ステップ 46
- 対象ファイル：`novel_50ep/tests/test_combat_rules.py`（新規）
- 目的：戦闘ルールを固定。
- 作業内容：装備消失・HP 増加・MP 増加の 3 パターンを `assert`。
- 受入基準：`pytest` が通る。

### ステップ 47
- 対象ファイル：`novel_50ep/generator.py`
- 目的：戦闘シーン生成で `CombatScene` を返す。
- 作業内容：戦闘生成後に `make_scene("combat", id=..., hp=..., mp=..., equipment=..., enemies=...)` を返すよう拡張。
- 受入基準：generator が `CombatScene` を返す。

### ステップ 48
- 対象ファイル：`novel_50ep/tests/test_generator_combat.py`（新規）
- 目的：戦闘の結合テスト。
- 作業内容：generator 出力を `tracker.feed` し、違反検出を `assert`。
- 受入基準：`pytest` が通る。

---

## Phase 6：探索シーンのルール（ステップ 49〜55）

### ステップ 49
- 対象ファイル：`novel_50ep/continuity_rules/exploration.yaml`（新規）
- 目的：探索用ルールファイルを作る。
- 作業内容：`version:1` と空 `rules` を書く。
- 受入基準：読める。

### ステップ 50
- 対象ファイル：`novel_50ep/continuity_rules/exploration.yaml`
- 目的：アイテム `subset` ルール。
- 作業内容：`type: exploration`, `op: subset`, `field: items`, `msg: "アイテムが消失"` を追加。
- 受入基準：アイテムが減ると違反。

### ステップ 51
- 対象ファイル：`novel_50ep/continuity_rules/exploration.yaml`
- 目的：位置継続ルール。
- 作業内容：`op: equals`, `field: location`, `msg: "場所が説明なしで変化"` を追加。
- 受入基準：location が変わると違反。

### ステップ 52
- 対象ファイル：`novel_50ep/scene_model.py`
- 目的：`ExplorationScene` の `items` を `to_dict` に含める。
- 作業内容：`to_dict` に `items` と `map_flags` を追加。
- 受入基準：ラウンドトリップで保存される。

### ステップ 53
- 対象ファイル：`novel_50ep/tests/test_exploration_rules.py`（新規）
- 目的：探索ルールを固定。
- 作業内容：アイテム消失・場所変化の 2 テスト。
- 受入基準：`pytest` が通る。

### ステップ 54
- 対象ファイル：`novel_50ep/generator.py`
- 目的：探索シーン生成で `ExplorationScene` を返す。
- 作業内容：探索生成後に `make_scene("exploration", id=..., location=..., items=..., map_flags=...)` を返す。
- 受入基準：generator が `ExplorationScene` を返す。

### ステップ 55
- 対象ファイル：`novel_50ep/tests/test_generator_exploration.py`（新規）
- 目的：探索の結合テスト。
- 作業内容：generator 出力を `tracker.feed` し違反検出を `assert`。
- 受入基準：`pytest` が通る。

---

## Phase 7：foreshadow_manager との連携（ステップ 56〜60）

### ステップ 56
- 対象ファイル：`novel_50ep/foreshadow_manager.py`
- 目的：伏線を `expect` リストとしてエクスポート。
- 作業内容：`def get_expects(self): return [{"id":f["id"], "type":f["scene_type"], "field":f["field"]} for f in self.foreshadows]` を追加。
- 受入基準：伏線が期待リストとして取得できる。

### ステップ 57
- 対象ファイル：`novel_50ep/continuity_rules/foreshadow.yaml`（新規）
- 目的：伏線ルールを動的生成する。
- 作業内容：`rule_engine.py` に `def build_foreshadow_rules(expects): return [{"type":e["type"],"op":"equals","field":e["field"],"msg":"伏線未回収"} for e in expects]` を追加。
- 受入基準：関数がルールリストを返す。

### ステップ 58
- 対象ファイル：`novel_50ep/continuity_tracker.py`
- 目的：伏線ルールを取り込む。
- 作業内容：`ContinuityTracker.__init__` で `self.rules += build_foreshadow_rules(expects)` を呼べるように引数 `expects` を追加（省略時は空）。
- 受入基準：伏線ルールが適用される。

### ステップ 59
- 対象ファイル：`novel_50ep/tests/test_foreshadow_link.py`（新規）
- 目的：連携を固定。
- 作業内容：`foreshadow_manager` に伏線を登録し、対応シーンで不一致になるケースを `assert`。
- 受入基準：`pytest` が通る。

### ステップ 60
- 対象ファイル：`novel_50ep/generator.py`
- 目的：生成時に `foreshadow_manager.get_expects()` を tracker に渡す。
- 作業内容：generator のメインループで `tracker = ContinuityTracker(rules_dir, expects=fsm.get_expects())` を生成するよう 1 行追加。
- 受入基準：generator 実行時に伏線ルールが有効。

---

## Phase 8：polish_tool / generator へのフック（ステップ 61〜64）

### ステップ 61
- 対象ファイル：`novel_50ep/polish_tool.py`
- 目的：校正前に tracker へ渡すフックを追加。
- 作業内容：`def polish(text, scene=None):` のシグネチャに `scene` を追加し、内部で `tracker.feed(scene)` の結果をログ出力するだけにする（まだ修正はしない）。
- 受入基準：`polish` が scene を受け取ってもクラッシュしない。

### ステップ 62
- 対象ファイル：`novel_50ep/polish_tool.py`
- 目的：違反時の自動修正プロンプト生成を追加。
- 作業内容：`if tracker.violations:` のとき「以下の矛盾を修正してください: {tracker.report()}」という文字列を `text` の先頭に付与して返す。
- 受入基準：違反があるとプロンプトが付く。

### ステップ 63
- 対象ファイル：`novel_50ep/generator.py`
- 目的：generator が polish を呼ぶ際に scene を渡す。
- 作業内容：既存の `polish(text)` 呼び出しを `polish(text, scene=scene)` に書き換える（1 箇所ずつ）。
- 受入基準：generator 実行で scene が polish に渡る。

### ステップ 64
- 対象ファイル：`novel_50ep/tests/test_polish_hook.py`（新規）
- 目的：Phase 8 を固定。
- 作業内容：違反ありシーンを `polish` に渡し、戻り文字列にレポート文言が含まれることを `assert`。
- 受入基準：`pytest` が通る。

---

## Phase 9：評価・UI・バッチ・CI・自動修正（ステップ 65〜72）

### ステップ 65
- 対象ファイル：`novel_50ep/score_reviewer.py`
- 目的：継続性ペナルティをスコアに反映。
- 作業内容：ステップ 5 の `# CONTINUITY_HOOK` 箇所で `score -= len(tracker.violations) * 0.5` を追加。
- 受入基準：違反があるとスコアが下がる。

### ステップ 66
- 対象ファイル：`novel_50ep/score_reviewer.py`
- 目的：レポートにセクション追加。
- 作業内容：戻り値の辞書に `"continuity_issues": tracker.report()` を追加。
- 受入基準：スコア結果に継続性セクションがある。

### ステップ 67
- 対象ファイル：`frontend/src/components/dialogs/SettingsModal.tsx`
- 目的：UI に Continuity Monitor スイッチを追加。
- 作業内容：既存のトグルコンポーネントを 1 つコピーし、`label="Continuity Monitor"` のチェックボックスを追加し、状態を `useState` で保持。
- 受入基準：画面にスイッチが表示される。

### ステップ 68
- 対象ファイル：`src/backend/routers/health.py`（または該当 API）
- 目的：UI スイッチとバックエンドを繋ぐ。
- 作業内容：フラグを受け取る POST エンドポイント `/api/continuity/check` を追加し、リクエスト本文のシーン JSON を `SceneBase.from_dict` で復元して `tracker.feed` し結果を返す。
- 受入基準：curl でエンドポイントが動く。

### ステップ 69
- 対象ファイル：`novel_50ep/batch_runner.py`
- 目的：バッチに tracker を組み込む。
- 作業内容：バッチループ内で各シーン生成後に `violations = tracker.feed(scene)` を呼び、違反を `batch_report.txt` に追記。
- 受入基準：バッチ実行でレポートが出力される。

### ステップ 70
- 対象ファイル：`novel_50ep/batch_runner.py`
- 目的：`--fix-continuity` フラグを追加。
- 作業内容：`argparse` に `--fix-continuity` を追加し、指定時は違反シーンに対して `polish` を再呼び出しして上書き保存。
- 受入基準：フラグ付き実行で自動修正が走る。

### ステップ 71
- 対象ファイル：`novel_50ep/tests/test_novel_50ep.py`
- 目的：CI 用統合テストを追加。
- 作業内容：`def test_continuity_full():` で全ルールファイルを読み、サンプル小説（数シーン）を `tracker` に流し、期待違反数と一致することを `assert`。
- 受入基準：`pytest novel_50ep/tests/test_novel_50ep.py` が通る。

### ステップ 72
- 対象ファイル：`src/backend/workflows/commercial_pipeline.py`（CI 設定）
- 目的：パイプラインに継続性チェックを組み込む。
- 作業内容：ワークフロー定義に `run: pytest novel_50ep/tests/test_novel_50ep.py` を含む `continuity_check` ジョブを追加し、失敗時はマージブロックとする記述を入れる。
- 受入基準：CI 上で継続性テストが実行される。

---

## 付録：実装順の依存関係

```
Phase0(1-6) → Phase1(7-15) → Phase2(16-24) → Phase3(25-32)
                                      ↓
                    Phase4(33-40) → Phase5(41-48) → Phase6(49-55)
                                      ↓
                            Phase7(56-60) → Phase8(61-64) → Phase9(65-72)
```

各ステップは前のステップの「受入基準」が満たされていれば独立して実装可能。低性能 LLM でも 1 ステップずつ `pytest` で緑を確認しながら進められる。

## まとめ

この 72 ステップにより、`ContinuityTracker` は官能シーンのみならず戦闘・会話・探索の全シーンで連続性を検証できるようになる。さらに `foreshadow_manager` の伏線、`polish_tool` の自動修正、`score_reviewer` の評価、`batch_runner` の一括処理、フロントエンド UI、CI パイプラインとシームレスに連携し、プロット一貫性のリスクを根本から低減できる。
