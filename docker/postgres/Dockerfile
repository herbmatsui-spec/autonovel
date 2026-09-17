# AutoNovel v5.0: Apache AGE (Graph DB) の独自ビルドを廃止し、
# 公式 pgvector 軽量イメージへ一本化（ビルド時間短縮 & クラッシュゼロ）
FROM pgvector/pgvector:pg16

# 初期化スクリプト等があれば必要に応じてコピー
COPY ./docker/postgres/init.sql /docker-entrypoint-initdb.d/init.sql
