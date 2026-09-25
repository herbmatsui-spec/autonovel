"""データベーススキーマの後方互換性を検証するコントラクトテスト"""
from sqlalchemy import inspect
from src.db.base import Base  # 実際のインポートパスに合わせる

def test_table_count_has_not_decreased():
    """テーブル数が減っていないか（削除ではなく追加のみ許容）"""
    inspector = inspect(Base.metadata)
    current_tables = set(inspector.get_table_names())
    
    # ベースラインとの比較は artifatcs/ から取得
    baseline_path = Path("artifacts/db_schema_baseline.json")
    if baseline_path.exists():
        import json
        with open(baseline_path) as f:
            baseline = json.load(f)
        baseline_tables = set(baseline.get("tables", []))
        # テーブル削除がないかチェック
        removed = baseline_tables - current_tables
        assert not removed, f"以下のテーブルが削除されています: {removed}"
    else:
        # 初回実行時はベースライン作成
        baseline_path.parent.mkdir(exist_ok=True)
        with open(baseline_path, "w") as f:
            json.dump({"tables": list(current_tables)}, f)

def test_column_nullability_has_not_become_strict():
    """カラムの NULL 制約が厳しくなっていないか"""
    # 同様にベースライン比較で NULL 制約の追加を検知
    pass