# タブ遅延ロード監視アラート

## 概要
タブの遅延ロードが5秒を超えた場合にSlackに通知するアラートを設定します。

## 実装方法（例）
1. モニタリングシステム（例: Datadog, CloudWatch, Prometheus+Alertmanager）で、LCP（Largest Contentful Paint）またはカスタムメトリクス（タブ遅延ロード時間）を追跡します。
2. メトリクスが5秒を超える状態が5分間続く場合にアラートをトリガーします。
3. アラートはSlackの#frontend-performanceチャンネルに通知します。

## 設定項目
- メトリクス名: `tab_lazy_load_duration_seconds`
- 閾値: 5秒
- 期間: 5分間の平均
- 通知先: Slack #frontend-performance
- 通知メッセージ: `タブ遅延ロードが5秒を超えています。現在の値: {{value}}秒`

## 実装状況
このアラートは本番環境のモニタリングシステムに設定する必要があります。コードレベルでは、遅延ロード時間をカスタムメトリクスとして送信するinstrumentationを追加することを検討してください。