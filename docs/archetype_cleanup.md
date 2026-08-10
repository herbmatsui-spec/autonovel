# アーキタイプファイル整理リスト

## 正規ファイル
- src/config/archetypes_new.py (正規)

## 非正規ファイル（整理対象）
- src/config/archetypes.py
- src/config/archetypes_ascii.py
- src/config/archetypes_fixed.py
- src/config/archetypes_min.py
- src/config/archetypes_stub.py
- src/config/archetypes_test.py

## � 処理方�針
非正規ファイルは _legacy サフィックスを付けてリネームし、src/config/__init__.py からのインポートを archetypes_new.py に統一する。