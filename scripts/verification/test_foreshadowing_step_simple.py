#!/usr/bin/env python3
"""ForeshadowingRegistrationStep の簡易テスト"""

import sys
import os

# プロジェクトルートを Python パスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

try:
    # インポートを試みる
    from src.services.pipeline_steps import ForeshadowingRegistrationStep
    from src.services.pipeline_base import WorkflowContext
    
    print("✅ インポート成功")
    
    # インスタンス作成を試みる
    step = ForeshadowingRegistrationStep()
    print("✅ インスタンス作成成功")
    
    # クラスの継承関係を確認
    from src.services.pipeline_base import WorkflowStep
    if isinstance(step, WorkflowStep):
        print("✅ WorkflowStep を継承していることを確認")
    else:
        print("❌ WorkflowStep を継承していない")
        sys.exit(1)
    
    # メソッドの存在を確認
    if hasattr(step, 'execute') and callable(getattr(step, 'execute')):
        print("✅ execute メソッドが存在することを確認")
    else:
        print("❌ execute メソッドが存在しない")
        sys.exit(1)
    
    print("🎉 すべての基本テストがパスしました！")
    
except Exception as e:
    print(f"❌ エラーが発生しました: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)