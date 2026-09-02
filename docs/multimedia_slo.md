# Multimedia SLO

| 指標 | 目標 | 測定方法 |
| --- | --- | --- |
| 可用性 | 99.5% | `/health` の 5xx 率 < 0.5% |
| レイテンシ (p95) | < 3 秒 | `multimedia_latency_seconds` ヒストグラム |
| エラー率 | < 5% | `multimedia_errors_total / multimedia_requests_total` |
| タスク完了率 | > 95% | `multimedia_tasks` テーブルで `status=completed` の割合 |

## 計測

- カウンタ: `src/backend/observability/health.py` の `_Metrics`
- エクスポート: `GET /metrics`
- アラート: `docker/grafana/alerts/multimedia.yaml`
