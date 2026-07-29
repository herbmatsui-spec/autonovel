"""
Main Entry Point
Command-line and GUI entry point for the Manual Processor application
"""

import argparse
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config.config import Config
from src.logger import setup_logger, get_logger
from src.orchestrator import DocumentOrchestrator


def main():
    """Main entry point for the application"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="手書きマニュアル処理システム - スキャンした手書きマニュアルをPDF化し、AIで要約して複数形式で出力します"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="処理するPDFファイルのパス"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output",
        help="出力ディレクトリ（デフォルト: output）"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Google AI Studio APIキー（環境変数GOOGLE_API_KEYまたはGEMINI_API_KEY）"
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="CLIモードで実行"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="GUIモードで実行（デフォルト）"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="詳細なログ出力"
    )
    parser.add_argument(
        "--compact-layout",
        action="store_true",
        help="コンパクトレイアウト（余白削減・文字拡大）で出力"
    )
    parser.add_argument(
        "--use-emojis",
        action="store_true",
        help="見出しや箇条書きに絵文字を挿入"
    )
    parser.add_argument(
        "--business-doc",
        action="store_true",
        help="標準的な業務文書として処理（マニュアルではなく一般的なビジネス文書形式で整理）"
    )
    parser.add_argument(
        "--include-tables",
        action="store_true",
        help="表抽出を要約に含める（オプトイン）"
    )
    parser.add_argument(
        "--remove-markdown-bold",
        action="store_true",
        default=True,
        help="Word出力時にMarkdown太字（**）を除去（デフォルト: 除去する）"
    )
    parser.add_argument(
        "--keep-markdown-bold",
        action="store_false",
        dest="remove_markdown_bold",
        help="Word出力時にMarkdown太字（**）を保持する"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="バージョン情報を表示"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(
        name="manual_processor",
        log_level=log_level,
        log_file=Path("logs/manual_processor.log")
    )
    
    logger = get_logger("main")
    
    # Handle version flag
    if args.version:
        print("手書きマニュアル処理システム v1.0.0")
        print("Google AI Studio APIを使用しています")
        sys.exit(0)
    
    # Handle API key
    if args.api_key:
        os.environ["GOOGLE_API_KEY"] = args.api_key
        os.environ["GEMINI_API_KEY"] = args.api_key
    
    try:
        # Initialize configuration
        config = Config.get_instance()
        
        # Update output directory if specified
        config.output_directory = Path(args.output)
        config.ensure_directories()
        
        # Validate configuration
        errors = config.validate()
        if errors:
            logger.error("Configuration errors:")
            for error in errors:
                logger.error(f"  - {error}")
            sys.exit(1)
        
        # Run in appropriate mode
        if args.cli or args.input:
            # CLI mode
            logger.info("CLIモードで起動")
            
            if args.input:
                input_str = args.input.strip()
                pdf_files = []
                paths = [p.strip() for p in input_str.split(",") if p.strip()]
                for p_str in paths:
                    p = Path(p_str)
                    if p.is_dir():
                        pdf_files.extend(list(p.rglob("*.pdf")))
                    elif p.is_file() and p.suffix.lower() == ".pdf":
                        pdf_files.append(p)
                        
                if not pdf_files:
                    logger.error(f"入力パスにPDFファイルが見つかりません: {args.input}")
                    sys.exit(1)
                
                print(f"--- 全 {len(pdf_files)} 件のPDFファイルの処理を開始します ---")
                orchestrator = DocumentOrchestrator()
                success_count = 0
                for idx, pdf_path in enumerate(pdf_files, 1):
                    print(f"[{idx}/{len(pdf_files)}] 処理中: {pdf_path.name}...")
                    result = orchestrator.process_file(
                        pdf_path,
                        compact_layout=args.compact_layout,
                        use_emojis=args.use_emojis,
                        is_business_doc=args.business_doc,
                        include_tables=args.include_tables,
                        remove_markdown_bold=args.remove_markdown_bold
                    )
                    if result.success:
                        success_count += 1
                        print("  ✅ 処理完了")
                        if result.data and "output_files" in result.data:
                            for file_type, file_path in result.data["output_files"].items():
                                if file_path:
                                    print(f"    {file_type.upper()}: {file_path}")
                    else:
                        print(f"  ❌ 処理失敗: {result.message}")
                print(f"\n✅ バッチ処理終了: {success_count} / {len(pdf_files)} 件成功")
            else:
                # CLI monitoring mode
                logger.info("ファイル監視モードで起動（Ctrl+Cで終了）")
                orchestrator = DocumentOrchestrator()
                orchestrator.compact_layout = args.compact_layout
                orchestrator.use_emojis = args.use_emojis
                orchestrator.is_business_doc = args.business_doc
                orchestrator.include_tables = args.include_tables
                orchestrator.remove_markdown_bold = args.remove_markdown_bold
                orchestrator.start()
        else:
            # GUI mode (default)
            logger.info("GUIモードで起動")
            try:
                from src.gui.main import main as gui_main
                gui_main()
            except ImportError as e:
                logger.warning(f"GUIモジュールの読み込みに失敗: {e}")
                logger.info("CLIモードで起動します（ファイル監視モード: Ctrl+Cで終了）...")
                orchestrator = DocumentOrchestrator()
                orchestrator.start()
        
    except KeyboardInterrupt:
        logger.info("キーボード割り込みにより終了")
        sys.exit(0)
    except Exception as e:
        logger.error(f"予期しないエラー: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()