# サービス重複比�較表

## �� 概要
src/backend/ と src/services/ に同名のサービスファイルが存在する場合の比�較を行い、どちらを正規とするかを決定する。

## 比�較表

| サービス | バックエンドファイル | サービスファイル | 行数 (バックエンド) | 行数 (サービス) | � 内容の違い | 正規 |
|---|---|---|---|---|---|---|
| PlotService | src/backend/plot_service.py | src/services/plot_service.py | 70行 | 19行 | バックエンドはテンション管理・プロット生成の複�雑ロジックを実装。サービスは単�純なリポジトリラッパー。 | src/services/plot_service.py |
| BibleService | src/backend/bible_service.py | src/services/bible_service.py | 44行 | 607行 | バックエンドはシンプルなクラス（おそらくスタブ）。サービスは詳細な聖書サービス実装を提供。 | src/services/bible_service.py |

## 決定
上記の通り、サービス�側の実装を正規とし、バックエンド�側はサービス�側への転送スタブに変更する（ステップ39、40参照）。