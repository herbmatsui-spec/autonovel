**Step 34**: ファイル: `manual_processor/src/text_processor.py`
- 関数名: `clean_extracted_text`
- 処理:
  - 引数: text (str)
  - 戻り値: str (クリーニングされたテキスト)
  - OCRでよく発生するノイズを除去
  - 縦棒文字（|）をIまたはlに変換するオプション（設定可能）
  - 数字とアルファベットの間の不要なスペースを削除
  - 日本語文字とアルファベットの間の不要なスペースを保持（日本語処理では基本的にスペースは入れない）
  - 連続する改行を最大2つに制限（段落間の空行を保つため）
  - 特殊文字の正規化（例: 全角スペースを半角スペースに、全角数字を半角数字に）
  - 制御文字の除去（タブ、改ページなどは保持するか検討）

**Step 35**: ファイル: `manual_processor/tests/test_text_processor.py`
- 関数名: `test_combine_ocr_results`
- 処理:
  - 複数のOCR結果を結合する関数のテスト
  - 空のリスト、単一要素、複数要素のケースをテスト
  - ページ間の区切りが正しく挿入されるかを確認
  - 改行文字やスペースの正規化が正しく行われるかをテスト

**Step 36**: ファイル: `manual_processor/tests/test_text_processor.py`
- 関数名: `test_clean_extracted_text`
- 処理:
  - テキストクリーニング関数のテスト
  - 各種OCRノイズパターンを用いたテスト
  - 縦棒の変換、余分なスペース除去、改行正規化など
  - 日本語テキストでの適切な処理を確認（日本語間のスペースは除去しない）

### フェーズ6: Gemini APIモジュール (Steps 37-44)

**Step 37**: ファイル: `manual_processor/src/gemini_processor.py`
- クラス名: `GeminiProcessor`
- 処理:
  - コンストラクタ: `__init__(self, api_key: Optional[str] = None, model_name: str = "gemini-pro")`
  - Google Generative AI SDKを初期化
  - APIキーは環境変数または明示的に渡された値を使用
  - セーフティ設定と生成パラメータ（temperature, max_output_tokensなど）を設定可能に
  - モデルの利用可能性をチェックするメソッドを提供

**Step 38**: ファイル: `manual_processor/src/gemini_processor.py`
- 関数名: `summarize_text`
- 処理:
  - GeminiProcessorのメソッド
  - 引数: text (str), target_audience (str, default="beginner"), max_length (Optional[int])
  - 戻り値: GeminiResult
  - プロンプトエンジニアリング:
    ```
    あなたは親切でわかりやすい説明が得意なインストラクターです。
    次の技術文書を{target_audience}レベルの初心者でも理解できるように、
    重要なポイントを簡潔にまとめてください。
    
    以下の点に注意してください：
    1. 専門用語は必ず平易な言語に言い換えるか、説明を加える
    2. 長い説明は箇条書きにして見やすくする
    3. 重要な概念は太字や見出しで強調する（出力形式がサポートする場合）
    4. 例や analogies を使って理解を助ける
    5. 出力は Markdown 形式でフォーマットしてください
    
    元のテキスト：
    {text}
    ```
  - トークン制限を考慮し、長すぎるテキストはチャンクに分割して処理
  - エラーハンドリング:
    - API例外: GeminiAPIError に変換
    - セーフティフィルタによるブロック: 特別な結果を返却（ブロックされた旨と元テキストの一部を返す）
    - 空の入力: 空の結果を返却

**Step 39**: ファイル: `manual_processor/src/gemini_processor.py`
- 関数名: `extract_key_points`
- 処理:
  - GeminiProcessorのメソッド
  - 引数: text (str), max_points (int, default=10)
  - 戻り値: List[str] (重要ポイントのリスト)
  - プロンプトエンジニアリング:
    ```
    あなたは技術文書の重要ポイントを抽出する専門家です。
    次のテキストから、初心者が最初に理解すべき重要なポイントを{max_points}つ以内で箇条書きにして抽出してください。
    
    各ポイントは：
    1. 1文で完結する簡潔な表現
    2. 専門用語は避け、必要最低限の用語のみ使用
    3. 具体的な数値や手順は含める
    4. 主観的な評価ではなく、客観的な事実を述べる
    
    出力形式：
    - ポイント1
    - ポイント2
    - ポイント3
    ...
    
    元のテキスト：
    {text}
    ```
  - 結果をパースして文字列のリストに変換
  - エラーハンドリングはsummarize_textと同様

**Step 40**: ファイル: `manual_processor/src/gemini_processor.py`
- 関数名: `process_document`
- 処理:
  - GeminiProcessorのメソッド
  - 引数: text (str), target_audience (str, default="beginner")
  - 戻り値: GeminiResult (summaryとkey_pointsの両方を含む)
  - summarize_textとextract_key_pointsを順次呼び出して結果を結合
  - エラーが発生した場合は、利用可能な結果を返すか、両方とも失敗した場合は例外を propagate

**Step 41**: ファイル: `manual_processor/tests/test_gemini_processor.py`
- 関数名: `test_gemini_processor_initialization`
- 処理:
  - GeminiProcessorの初期化をテスト
  - 有効および無効なAPIキーでテスト
  - モデル名の指定が正しく機能するかをテスト

**Step 42**: ファイル: `manual_processor/tests/test_gemini_processor.py`
- 関数名: `test_summarize_text`
- 処理:
  - モックを使用したテキスト要約のテスト
  - Gemini APIのモックレスポンスを作成
  - 返却される要約が正しい形式かを検証
  - エラーケース（APIエラー、セーフティフィルターブロック、空入力）もテスト

**Step 43**: ファイル: `manual_processor/tests/test_gemini_processor.py`
- 関数名: `test_extract_key_points`
- 処理:
  - モックを使用した重要ポイント抽出のテスト
  - 箇条書き形式のモックレスポンスを作成
  - 返却されるポイントリストが正しくパースされるかを検証
  - エラーケースとフォーマットが崩れたレスポンスの処理もテスト

**Step 44**: ファイル: `manual_processor/tests/test_gemini_processor.py`
- 関数名: `test_process_document`
- 処理:
  - 文書処理統合メソッドのテスト
  - 要約とキーポイント抽出の両方が正しく行われるかを確認
  - 片方しか成功しなかった場合のフォールバック動作をテスト

### フェーズ7: 出力生成モジュール (PDF, Word, Audio) (Steps 45-56)

**Step 45**: ファイル: `manual_processor/src/pdf_generator.py`
- 関数名: `create_formatted_pdf`
- 処理:
  - 引数: content (GeminiResult), output_path (Path), title (str, default="処理済みマニュアル")
  - 戻り値: Path (生成されたPDFファイルパス)
  - レポートラボまたはFPDF2を使用してPDFを生成
  - フォント設定: 日本語フォントを適切に設定（IPAexGothic または Noto Sans CJK JP を使用）
  - スタイル設定:
    - タイトル: 大きめのフォント、中央揃え、太字
    - セクション見出し: 中くらいのフォント、左揃え、太字、上部に余白
    - 本文: 標準フォント、左揃え、適切な行間
    - コードブロック等:等幅フォント、背景色をつける（可能なら）
  - 箇条書きの適切なインデント処理
  - 改ページの適切な処理
  - エラーハンドリング:
    - フォントファイルが見つからない場合: デフォルトフォントにフォールバックし警告
    - ディスク書き込みエラー: IOError を送出
    - メモリ不足: MemoryError を送出

**Step 46**: ファイル: `manual_processor/src/docx_generator.py`
- 関数名: `create_word_document`
- 処理:
  - 引数: content (GeminiResult), output_path (Path), title (str, default="処理済みマニュアル")
  - 戻り値: Path (生成されたWord文書パス)
  - python-docxを使用して.docxファイルを生成
  - スタイル設定:
    - タイトル: 见出し1スタイル、中央揃え
    - セクション見出し: 见出し2スタイル、左揃え
    - 本文: 通常スタイル、左揃え
    - 箇条書き: リストスタイルを適用
  - 目次（Table of Contents）の自動生成を検討（オプション機能）
  - ヘッダー・フッターにページ番号とドキュメントタイトルを追加（オプション）
  - エラーハンドリング:
    - テンプレートやスタイルの問題: ValueError
    - ディスク書き込みエラー: IOError

**Step 47**: ファイル: `manual_processor/src/audio_generator.py`
- クラス名: `AudioGenerator`
- 処理:
  - コンストラクタ: `__init__(self, language_code: str = "ja-JP", voice_name: str = "ja-JP-Standard-A")`
  - Google Cloud Text-to-Speechクライアントを初期化
  - 音声合成の設定（話速、ピッチ、ボリューム）を保存
  
**Step 48**: ファイル: `manual_processor/src/audio_generator.py`
- 関数名: `create_audio_summary`
- 処理:
  - AudioGeneratorのメソッド
  - 引数: key_points (List[str]), output_path (Path), 
        language_code (str, default="ja-JP"), 
        voice_name (str, default="ja-JP-Standard-A"),
        speaking_rate (float, default=1.0),
        pitch (float, default=0.0)
  - 戻り値: Path (生成された音声ファイルパス)
  - キーポイントリストを一つのテキストに結合（適切な間隔を置く）
  - SSML（Speech Synthesis Markup Language）を使用して自然な話し方を調整可能に
    - 句読点での休止を明示
    - 数字の読み方を指定（例: 「2023年」ではなく「にせんにじゅうさんねん」）
    - 強調したい単語をマークアップ
  - 音声フォーマット: MP3（線形16bit WAVから変換でも可）
  - エラーハンドリング:
    - API例外: TTSError に変換
    - テキストが長すぎる場合: チャンクに分割して複数ファイルに出力
    - 無効な言語コードまたはボイス名: ValueError

**Step 49**: ファイル: `manual_processor/tests/test_pdf_generator.py`
- 関数名: `test_create_formatted_pdf`
- 処理:
  - PDF生成関数のテスト
  - 簡単なGeminiResultオブジェクトを作成
  - PDFが正常に生成されるかを確認
  - 生成されたPDFの基本プロパティ（ページ数など）をチェック
  - フォント関連のエラーケースもテスト

**Step 50**: ファイル: `manual_processor/tests/test_docx_generator.py`
- 関数名: `test_create_word_document`
- 処理:
  - Word文書生成関数のテスト
  - 簡単なGeminiResultオブジェクトを作成
  - Word文書が正常に生成されるかを確認
  - 生成された文書の基本プロパティ（段落数、スタイル適用など）をチェック

**Step 51**: ファイル: `manual_processor/tests/test_audio_generator.py`
- 関数名: `test_audio_generator_initialization`
- 処理:
  - AudioGeneratorの初期化をテスト
  - デフォルトおよびカスタムパラメータでテスト

**Step 52**: ファイル: `manual_processor/tests/test_audio_generator.py`
- 関数名: `test_create_audio_summary`
- 処理:
  - モックを使用した音声合成のテスト
  - TTS APIのモックレスポンスを作成
  - 音声ファイルが正常に生成されるかを確認
  - エラーケース（APIエラー、無効なパラメータ）もテスト
  - 長いテキストのチャンク分割機能もテスト

**Step 53**: ファイル: `manual_processor/src/output_formatter.py`
- 関数名: `format_output_filename`
- 処理:
  - 出力ファイル名を生成するユーティリティ関数
  - 引数: base_name (str), extension (str), include_timestamp (bool, default=True)
  - 戻り値: str (フォーマットされたファイル名)
  - ベース名から拡張子を除去し、タイムスタンプ（YYYYMMDD_HHMMSS）を追加するオプション
  - セーファーなファイル名に変換（Step 12のget_safe_filenameを再利用）
  - 例: "manual" + "_20231201_143022" + ".pdf" → "manual_20231201_143022.pdf"

**Step 54**: ファイル: `manual_processor/tests/test_output_formatter.py`
- 関数名: `test_format_output_filename`
- 処理:
  - ファイル名フォーマット関数のテスト
  - タイムスタンプあり/なしの両方をテスト
  - 拡張子の扱いをテスト（入力に拡張子がある/なしの両方）
  - 安全でない文字の処理をテスト

**Step 55**: ファイル: `manual_processor/src/output_manager.py`
- 関数名: `save_all_formats`
- 処理:
  - すべての出力形式（PDF, Word, Audio）を一括で保存する関数
  - 引数: content (GeminiResult), base_output_path (Path), config (AppConfig)
  - 戻り値: OutputFiles (生成されたファイル情報のデークラスまたはNamedTuple)
  - 内部処理:
    1. ベースファイル名を抽出（入力PDFのファイル名から拡張子を除いたもの）
    2. 各フォーマットのファイル名を生成（PDF, DOCX, MP3）
    3. 出力ディレクトリが存在しない場合は作成
    4. 各形式のジェネレーターを呼び出してファイルを生成
    5. 成功したファイルのみを結果に含める（一部失敗しても他は続行）
    6. 生成結果とエラー情報を含むオブジェクトを返却

**Step 56**: ファイル: `manual_processor/tests/test_output_manager.py`
- 関数名: `test_save_all_formats`
- 処理:
  - 出力一括保存関数のテスト
  - モックを使用して各ジェネレーターを置き換え
  - 正常系: すべての形式が生成されるかを確認
  - 部分失敗: 一部の形式が失敗しても他は成功するかを確認
  - ディレクトリ作成機能のテスト

### フェーズ8: エラーハンドリングとロギング (Steps 57-60)

**Step 57**: ファイル: `manual_processor/src/logger.py`
- 関数名: `setup_logger`
- 処理:
  - アプリケーション全体で使用するロガーを設定
  - 引数: name (str), log_level (str, default="INFO"), log_file (Optional[Path])
  - 戻り値: logging.Logger インスタンス
  - フォーマッター: '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
  - ハンドラー:
    - コンソールハンドラー (StreamFormatter)
    - ファイルハンドラー (RotatingFileHandler, 10MB × 5ファイル)
  - ロガーの伝播を防止（重複ログを避けるため）
  - サードパーティライブラリのログレベルを適切に調整（例: urllib3, google.api_core）

**Step 58**: ファイル: `manual_processor/src/error_handler.py`
- クラス名: `ErrorHandler`
- 処理:
  - エラーの集約処理とユーザー通知を行うクラス
  - エラーカウントとレートリミッティング機能
  - ユーザーへの通知方法:
    - コンソールエラーメッセージ
    - システムトレイ通知（Windows 10/11、plyerまたはwin10toast使用）
    - ログファイルへの詳細記録
  - エラー分類:
    - 一時的なエラー（ネットワーク、レートリミット）: リトライ推奨
    - 永続的なエラー（ファイル不Found、認証エラー）: ユーザー介入必要
    - 回復可能なエラー（一時ファイルエラー）: 自動復旧を試みる
  - メソッド: `handle_error(error: Exception, context: str = "", show_user_notification: bool = True) -> bool`
    - 戻り値: True if recovery was attempted/possible, False otherwise

**Step 59**: ファイル: `manual_processor/tests/test_logger.py`
- 関数名: `test_setup_logger`
- 処理:
  - ロガー設定関数のテスト
  - ログレベル別の出力を確認
  - ファイル出力とコンソール出力の両方をテスト
  - ローテーション機能の簡易テスト

**Step 60**: ファイル: `manual_processor/tests/test_error_handler.py`
- 関数名: `test_error_handler`
- 処理:
  - エラーハンドラーのテスト
  - 各種例外タイプでの処理をテスト
  - ユーザー通知の発火条件をテスト
  - エラーカウントとレートリミッティング機能をテスト

### フェーズ9: メインオーケストレーション (Steps 61-64)

**Step 61**: ファイル: `manual_processor/src/orchestrator.py`
- クラス名: `DocumentProcessingOrchestrator`
- 処理:
  - すべてのコンポーネントを調整するメインクラス
  - コンストラクタ: `__init__(self, config: AppConfig)`
  - 初期化時にすべてのサブコンポーネントを作成:
    - USBMonitor
    - OCRProcessor
    - GeminiProcessor
    - AudioGenerator
    - PDFGenerator, DOCXGenerator
    - Logger, ErrorHandler
  - 内部状態管理:
    - 処理中のファイルセット（重複処理防止）
    - 完了したファイルセット（成功記録）
    - 失敗したファイルセット（失敗記録とリトライカウント）
  - メインループ: `_processing_loop` - キューベースまたはイベント駆動でファイルを処理
  - シャットダウンハンドリング: SIGTERM、SIGINT、Windowsシャットダウンイベントを捕捉

**Step 62**: ファイル: `manual_processor/src/orchestrator.py`
- 関数名: `process_single_file`
- 処理:
  - Orchestratorのメソッド
  - 引数: file_path (Path)
  - 戻り値: ProcessingResult (成功/失敗、生成ファイルリスト、エラー情報)
  - 処理フロー:
    1. ファイルの存在とアクセス権限をチェック
    2. ファイルサイズをチェック（設定値超過ならスキップ）
    3. 一時ファイル名を生成（処理中マーク）
    4. PDFの妥当性をチェック
    5. PDFから画像を抽出
    6. 各画像に対してOCRを実行
    7. OCR結果を結合・クリーニング
    8. テキストが空でないかチェック
    9. Geminiで要約とキーポイント抽出
    10. 結果が空でないかチェック
    11. すべての出力形式（PDF, Word, Audio）を生成
    12. 一時ファイルを削除
    13. 結果を返却
  - エラーハンドリング: 各ステップで例外をキャッチし、適切なエラーラップを行う
  - クリーンアップ: 例外が発生しても一時ファイルは必ずクリーンアップ

**Step 63**: ファイル: `manual_processor/src/orchestrator.py`
- 関数名: `start_processing`
- 処理:
  - Orchestratorのメソッド
  - USB監視を開始し、メイン処理ループに入る
  - シグナルハンドラーを設定（終了シグナルを捕捉）
  - メインループでは:
    - キューからファイルを取り出す（またはイベント駆動で）
    - 処理中ではないファイルのみを処理対象に
    - process_single_fileを呼び出す
    - 結果に応じて成功/失敗セットを更新
    - 定期的に統計情報をログ出力
    - シャットダウンシグナルが来たらループを脱出
  - 終了時のクリーンアップ処理

**Step 64**: ファイル: `manual_processor/tests/test_orchestrator.py`
- 関数名: `test_orchestrator_initialization`
- 処理:
  - Orchestratorの初期化をテスト
  - すべてのサブコンポーネントが正しく作成されるかを確認

**Step 65**: ファイル: `manual_processor/tests/test_orchestrator.py`
- 関数名: `test_process_single_file_success`
- 処理:
  - モックを使用した単一ファイル処理の成功ケースをテスト
  - 各ステージのモックを準備し、正常なフローをシミュレート
  - 期待される結果が返されるかを確認

**Step 66**: ファイル: `manual_processor/tests/test_orchestrator.py`
- 関数名: `test_process_single_file_failure`
- 処理:
  - 各ステージでの失敗ケースをテスト
  - PDFが無効な場合の処理
  - OCR失敗時の処理
  - Gemini API失敗時の処理
  - 出力生成失敗時の処理
  - 適切なエラーが返されるかを確認

### フェーズ10: GUI実装 (Steps 67-70)

**Step 67**: ファイル: `manual_processor/src/gui/main_window.py`
- クラス名: `MainWindow` (继承自 QMainWindow または Tkinter の Tk)
- 処理:
  - PySide6を使用したGUIのメインウィンドウを実装
  - UI要素:
    - タイトルバー: "手動書マニュアル処理システム"
    - ステータスバー: 現在の状態と統計情報を表示
    - メニューバー:
      * ファイル: 設定、終了
      * 監視: USB監視の開始/停止、手動フォルダ選択
      * ヘルプ: 使い方、バージョン情報
    - 中央パネル:
      * USBドライブ選択コンボボックス（リフレッシュボタン付き）
      * 監視状態表示ラベル（ランプアイコンで色分け）
      * 処理待ちファイルリスト（テーブルビュー）
      * 処理完了ファイルリスト（テーブルビュー）
      * 処理失敗ファイルリスト（テーブルビュー）
      * 統計情報パネル（今日処理したファイル数、成功率など）
      * ログ表示エリア（折りたたみ可能、ログレベルフィルタ付き）
  - シグナルとスロット:
    - USBモニターからのファイル検出シグナルを受けて処理キューに追加
    - オーケストレーターからの進捗更新シグナルを受けてUIを更新
    - エラーハンドラーからの通知を受けてポップアップまたはステータス表示
  - 初期化時に設定をロードし、コンポーネントを初期化

**Step 68**: ファイル: `manual_processor/src/gui/settings_dialog.py`
- クラス名: `SettingsDialog` (继承自 QDialog)
- 処理:
  - 設定を編集するためのダイアログウィンドウ
  - タブbedインターフェース:
    - 一般設定: 出力ディレクトリ、一時ディレクトリ、ログレベル
    - USB監視設定: 監視するドライブ、ポーリング間隔
    - OCR設定: DPI、言語ヒント、信頼度閾値
    - Gemini設定: モデル名、温度、最大トークン数
    - TTS設定: 言語、ボイス、話速、ピッチ
    - 高度な設定: 同時処理数、リトライ回数、タイムアウト
  - 各フィールドに適切な入力コントロール（テキストボックス、スピンボックス、コンボボックス、チェックボックス）
  - バリデーション: 入力値の範囲チェックと必須フィールドチェック
  - OK/Cancelボタン: OK時に設定を保存しアプリケーションに通知、Cancel時に変更を破棄
  - デフォルト値へのリセットボタン
  - 設定のインポート/エクスポート機能（JSON形式）

**Step 69**: ファイル: `manual_processor/src/gui/app.py`
- 関数名: `main`
- 処理:
  - GUIアプリケーションのエントリーポイント
  - QApplicationの初期化
  - 言語設定（日本語）の適用
  - スタイルシートの適用（オプション、モダンな外観のために）
  - MainWindowのインスタンス作成と表示
  - イベントループの開始
  - 例外ハンドラー: 予期しない例外をキャッチしてエラーダイアログを表示
  - 終了時のクリーンアップ処理（オーケストレーターの停止など）

**Step 70**: ファイル: `manual_processor/tests/test_gui.py`
- 関数名: `test_main_window_creation`
- 処理:
  - メインウィンドウが正常に作成されるかをテスト
  - 基本的なUI要素が存在するかを確認

**Step 71**: ファイル: `manual_processor/tests/test_gui.py`
- 関数名: `test_signal_slot_connections`
- 処理:
  - GUIのシグナルとスロット接続が正しく設定されているかをテスト
  - モックオブジェクトを使用して、シグナル発信時に適切なスロットが呼び出されるかを確認

### フェーズ11: 最終統合とテスト (Step 72)

**Step 72**: ファイル: `manual_processor/main.py`
- 関数名: `main`
- 処理:
  - アプリケーションのメインエントリーポイント（CLIおよびGUI両方をサポート）
  - コマンドライン引数の解析:
    * `--gui`: GUIモードで起動（デフォルト）
    * `--cli`: CLIモードで起動
    * `--config <path>`: カスタム設定ファイルパス
    * `--verbose`: 詳細なログ出力
    * `--version`: バージョン情報を表示して終了
  - 環境変数から設定をロード（.envファイルもサポート）
  - 必要なディレクトリを作成（出力、一時、ログディレクトリ）
  - ロガーの初期化
  - モードに応じて処理を分岐:
    - GUIモード: gui.app.main() を呼び出す
    - CLIモード: 
      * 単一ファイル処理モード: 指定されたPDFファイルを処理して終了
      * ディレクトリ監視モード: 指定ディレクトリを監視して継続処理
      * バッチ処理モード: 指定ディレクトリ内のすべてのPDFを処理して終了
  - 例外ハンドラートップレベル:
    * 予期しない例外をキャッチしてログに記録し、ユーザーにわかりやすいエラーメッセージを表示
    * 終了コードを適切に設定（0: 成功, 1: エラー, 2: 使用方法エラーなど）
  - クリーンアップハンドラー:
    * SIGINT (Ctrl+C) と SIGTERM を捕捉して graceful shutdown
    * Windowsコンソールコントロールハンドラーも設定
  - リソースクリーンアップ:
    * オーケストレーターの停止
    * 一時ファイルのクリーンアップ
    * ログハンドラーのフラッシュとクローズ
```