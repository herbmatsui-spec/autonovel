"""
Tkinter GUI Application
Provides a graphical interface for the manual processor
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from pathlib import Path
import os
import webbrowser

from config.config import Config
from src.processor.processor import DocumentProcessor
from src.logger import get_logger

logger = get_logger("gui")


class ToolTip:
    """Create a tooltip for a given widget"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert") if hasattr(self.widget, "bbox") and self.widget.bbox("insert") else (0, 0, 0, 0)
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            foreground="#000000",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Segoe UI", 9, "normal"),
            padx=8,
            pady=4
        )
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


class ManualProcessorGUI(tk.Tk):
    """Main GUI application window"""
    
    def __init__(self):
        super().__init__()
        self.title("手書きマニュアル処理システム")
        self.geometry("820x650")
        self.resizable(True, True)
        
        # Initialize components
        self.config = Config.get_instance()
        self.processor = None
        self.is_processing = False
        
        # Setup UI
        self.setup_ui()
        self.center_window()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Create main frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        # Configure grid weights
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(7, weight=1)
        
        # Header / Title section with Help Button
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=3, pady=(0, 15), sticky=(tk.W, tk.E))
        header_frame.columnconfigure(0, weight=1)

        title_label = ttk.Label(
            header_frame, 
            text="手書きマニュアル処理システム", 
            font=("Meiryo", 16, "bold")
        )
        title_label.grid(row=0, column=0, sticky=tk.W)

        help_btn = ttk.Button(
            header_frame,
            text="❓ 使い方ヘルプ",
            command=self.show_help_dialog
        )
        help_btn.grid(row=0, column=1, sticky=tk.E)
        ToolTip(help_btn, "使い方の基本手順や各設定項目の解説ダイアログを開きます。")
        
        # File selection section
        file_label = ttk.Label(main_frame, text="対象ファイル/フォルダ:")
        file_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        ToolTip(file_label, "解析したいPDFファイル、または複数PDFが入ったフォルダを指定します。")
        
        self.file_path_var = tk.StringVar()
        file_entry = ttk.Entry(
            main_frame, 
            textvariable=self.file_path_var, 
            width=40
        )
        file_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=5)
        ToolTip(file_entry, "指定されたPDFのパスが表示されます。複数ファイルはセミコロン(;)区切りです。")
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=2, padx=(5, 0), pady=5)
        
        browse_files_btn = ttk.Button(
            btn_frame, 
            text="ファイル選択...", 
            command=self.browse_files
        )
        browse_files_btn.pack(side=tk.LEFT, padx=2)
        ToolTip(browse_files_btn, "パソコン内のPDFファイルを1つ以上選択します（CtrlやShiftで複数選択可）。")
        
        browse_folder_btn = ttk.Button(
            btn_frame, 
            text="フォルダ選択...", 
            command=self.browse_folder
        )
        browse_folder_btn.pack(side=tk.LEFT, padx=2)
        ToolTip(browse_folder_btn, "フォルダー内のすべてのPDFを一括処理したい場合に選択します。")
        
        # API Key section
        api_label = ttk.Label(main_frame, text="APIキー:")
        api_label.grid(row=2, column=0, sticky=tk.W, pady=(15, 5))
        ToolTip(api_label, "Google Gemini APIを利用するためのAPIキーです。")
        
        self.api_key_var = tk.StringVar()
        api_key_from_env = os.environ.get("GOOGLE_API_KEY", "")
        self.api_key_var.set(api_key_from_env)
        
        api_entry = ttk.Entry(
            main_frame, 
            textvariable=self.api_key_var, 
            width=40,
            show="*"
        )
        api_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=(15, 5))
        ToolTip(api_entry, "Google AI Studioで取得したGemini APIキー（AIzaSy...など）を入力してください。")
        
        self.show_key_var = tk.BooleanVar()
        show_check = ttk.Checkbutton(
            main_frame,
            text="表示",
            variable=self.show_key_var,
            command=self.toggle_api_key_visibility
        )
        show_check.grid(row=2, column=2, sticky=tk.W, padx=(5, 0), pady=(15, 5))
        ToolTip(show_check, "チェックを入れると入力したAPIキーが画面上にテキスト表示されます。")
        
        # Options Label Frame
        options_group = ttk.LabelFrame(main_frame, text=" ⚙️ 変換オプション（初心者向けカスタマイズ） ", padding=10)
        options_group.grid(row=3, column=0, columnspan=3, pady=(15, 10), sticky=(tk.W, tk.E))
        
        self.compact_layout_var = tk.BooleanVar()
        compact_check = ttk.Checkbutton(
            options_group,
            text="コンパクトレイアウト（余白削減・文字拡大）",
            variable=self.compact_layout_var
        )
        compact_check.grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        ToolTip(compact_check, "印刷や閲覧時に見やすいよう、ページの余白を小さくし文字サイズをやや大きめに配置します。")
        
        self.use_emojis_var = tk.BooleanVar()
        emoji_check = ttk.Checkbutton(
            options_group,
            text="見出しに絵文字を自動挿入",
            variable=self.use_emojis_var
        )
        emoji_check.grid(row=0, column=1, sticky=tk.W, padx=5, pady=3)
        ToolTip(emoji_check, "生成されるWord/PDF文書の見出しに親しみやすいアイコン絵文字（📝, 💡など）を付与します。")
        
        self.is_business_doc_var = tk.BooleanVar()
        business_check = ttk.Checkbutton(
            options_group,
            text="標準業務文書モード",
            variable=self.is_business_doc_var
        )
        business_check.grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        ToolTip(business_check, "一般的な社内マニュアル・報告書向けに正統派かつ見やすいビジネスフォント・書式で出力します。")
        
        self.include_tables_var = tk.BooleanVar()
        tables_check = ttk.Checkbutton(
            options_group,
            text="表組み(テーブル)自動認識を含める",
            variable=self.include_tables_var
        )
        tables_check.grid(row=1, column=1, sticky=tk.W, padx=5, pady=3)
        ToolTip(tables_check, "手書きマニュアル内の表（罫線枠）をAIが分析し、綺麗なWord表組みとして整形出力します。")
        
        self.remove_markdown_bold_var = tk.BooleanVar(value=True)
        bold_check = ttk.Checkbutton(
            options_group,
            text="Markdown太字記号 (**) をきれいに除去",
            variable=self.remove_markdown_bold_var
        )
        bold_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=3)
        ToolTip(bold_check, "AI応答に含まれる『**文字**』というMarkdown表記を取り除き、自然な太字書式へと変換します。")
        
        # Process button
        self.process_btn = ttk.Button(
            main_frame,
            text="🚀 処理を開始する",
            command=self.start_processing,
            style="Accent.TButton"
        )
        self.process_btn.grid(row=4, column=0, columnspan=3, pady=10)
        ToolTip(self.process_btn, "選択されたPDFファイルをAIが読み込み、PDF・Word・MP3音声の作成を開始します。")
        
        # Progress bar
        self.progress = ttk.Progressbar(
            main_frame,
            mode='indeterminate'
        )
        self.progress.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status text area
        status_label = ttk.Label(main_frame, text="処理進捗・ログ:")
        status_label.grid(row=6, column=0, sticky=tk.NW, pady=(5, 5))
        ToolTip(status_label, "AIの文字起こしや文書生成の進行状況メッセージがリアルタイムで表示されます。")
        
        self.status_text = tk.Text(
            main_frame,
            height=8,
            width=70,
            wrap=tk.WORD
        )
        self.status_text.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        scrollbar = ttk.Scrollbar(
            main_frame,
            orient=tk.VERTICAL,
            command=self.status_text.yview
        )
        scrollbar.grid(row=7, column=3, sticky=(tk.N, tk.S), pady=(0, 10))
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(7, weight=1)
        
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"))

    def show_help_dialog(self):
        """Show easy-to-understand help modal for beginners"""
        help_window = tk.Toplevel(self)
        help_window.title("使い方ヘルプ・ガイド")
        help_window.geometry("600x480")
        help_window.resizable(False, False)
        
        # Make modal
        help_window.transient(self)
        help_window.grab_set()
        
        frame = ttk.Frame(help_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        title = ttk.Label(frame, text="📖 初心者向け使い方ガイド", font=("Meiryo", 14, "bold"))
        title.pack(anchor=tk.W, pady=(0, 10))
        
        help_text = (
            "【基本の使い方 3ステップ】\n"
            "1. 「ファイル選択」ボタンを押して、文字起こししたいPDFを選びます。\n"
            "   （フォルダ単位でまとめて一括処理したい場合は「フォルダ選択」を押します）\n\n"
            "2. 「APIキー」欄に Google Gemini の APIキーを入力します。\n"
            "   ※設定済みの場合は自動表示されます。\n\n"
            "3. 画面中央の「🚀 処理を開始する」ボタンを押すと自動解析が始まります。\n\n"
            "--------------------------------------------------\n"
            "【出力される成果物】\n"
            "処理完了後、アプリと同じ場所にある `output` フォルダ内に以下が生成されます：\n"
            " ・📄 整形済みPDFドキュメント\n"
            " ・📝 編集可能な Word (.docx) ファイル\n"
            " ・🎧 読み上げ用 MP3 音声ファイル\n"
            " ・📱 音声にアクセスできる QRコード\n\n"
            "【オプション機能について】\n"
            " 各項目にマウスカーソルを乗せると（ホバーすると）説明が表示されます。"
        )
        
        msg_label = ttk.Label(frame, text=help_text, justify=tk.LEFT, font=("Segoe UI", 9.5))
        msg_label.pack(anchor=tk.W, fill=tk.BOTH, expand=True, pady=5)
        
        close_btn = ttk.Button(frame, text="閉じる", command=help_window.destroy)
        close_btn.pack(anchor=tk.E, pady=(10, 0))

    
    def center_window(self):
        """Center the window on screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def browse_files(self):
        """Open file dialog to select multiple PDF files"""
        file_paths = filedialog.askopenfilenames(
            title="PDFファイルを選択（複数選択可）",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file_paths:
            self.file_path_var.set("; ".join(file_paths))
            self.log_message(f"ファイル選択 ({len(file_paths)}件): {', '.join(Path(p).name for p in file_paths)}")
            
    def browse_folder(self):
        """Open directory dialog to select folder containing PDFs"""
        folder_path = filedialog.askdirectory(title="PDFが含まれるフォルダを選択")
        if folder_path:
            self.file_path_var.set(folder_path)
            self.log_message(f"フォルダ選択: {folder_path}")
    
    def toggle_api_key_visibility(self):
        """Toggle API key visibility"""
        if self.show_key_var.get():
            for widget in self.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Entry) and widget.winfo_children().index(child) == 1:
                            child.configure(show="")
                            break
        else:
            for widget in self.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Entry) and widget.winfo_children().index(child) == 1:
                            child.configure(show="*")
                            break
    
    def log_message(self, message: str):
        """Add a message to the status text area"""
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.update_idletasks()
    
    def start_processing(self):
        """Start the processing workflow for single, multiple, or directory PDF inputs"""
        input_str = self.file_path_var.get().strip()
        if not input_str:
            messagebox.showerror("エラー", "ファイルまたはフォルダを選択してください")
            return
        
        # Collect target PDF files
        pdf_files = []
        paths = [p.strip() for p in input_str.split(";") if p.strip()]
        
        for p_str in paths:
            p = Path(p_str)
            if p.is_dir():
                pdf_files.extend(list(p.rglob("*.pdf")))
            elif p.is_file() and p.suffix.lower() == ".pdf":
                pdf_files.append(p)
                
        if not pdf_files:
            messagebox.showerror("エラー", "処理対象のPDFファイルが見つかりませんでした")
            return
            
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showerror("エラー", "APIキーを入力してください")
            return
        
        os.environ["GOOGLE_API_KEY"] = api_key
        if "GEMINI_API_KEY" not in os.environ:
            os.environ["GEMINI_API_KEY"] = api_key
        
        self.process_btn.configure(state="disabled")
        self.progress.start(10)
        self.is_processing = True
        
        self.log_message(f"--- 全 {len(pdf_files)} 件のPDFファイルの処理を開始します ---")
        
        thread = threading.Thread(target=self.process_batch, args=(pdf_files,))
        thread.daemon = True
        thread.start()
    
    def process_batch(self, pdf_files: list):
        """Process batch of PDF files in background thread"""
        results = []
        compact = self.compact_layout_var.get()
        use_emojis = self.use_emojis_var.get()
        is_business_doc = self.is_business_doc_var.get()
        include_tables = self.include_tables_var.get()
        remove_markdown_bold = self.remove_markdown_bold_var.get()
        try:
            self.processor = DocumentProcessor()
            for idx, pdf_path in enumerate(pdf_files, 1):
                self.after(0, self.log_message, f"[{idx}/{len(pdf_files)}] 処理中: {pdf_path.name}")
                res = self.processor.process_pdf(pdf_path, compact_layout=compact, use_emojis=use_emojis, is_business_doc=is_business_doc, include_tables=include_tables, remove_markdown_bold=remove_markdown_bold)
                results.append(res)
                if res["success"]:
                    self.after(0, self.log_message, f"  └ 完了! タイトル: 【{res.get('title', '無題')}】")
                else:
                    self.after(0, self.log_message, f"  └ 失敗: {res.get('error', '不明なエラー')}")
                    
            self.after(0, self.batch_complete, results)
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            self.after(0, self.processing_error, str(e))
            
    def batch_complete(self, results: list):
        """Handle batch completion"""
        self.progress.stop()
        self.process_btn.configure(state="normal")
        self.is_processing = False
        
        success_count = sum(1 for r in results if r.get("success"))
        total_count = len(results)
        
        self.log_message(f"✅ バッチ処理完了: 全{total_count}件中 {success_count}件が正常終了しました！")
        
        messagebox.showinfo(
            "処理完了",
            f"バッチ処理が完了しました！\n\n■ 成功: {success_count} / {total_count} 件\n\n出力フォルダ（output/）を確認してください。"
        )
    
    def processing_error(self, error_msg: str):
        """Handle processing error"""
        self.progress.stop()
        self.process_btn.configure(state="normal")
        self.is_processing = False
        
        self.log_message(f"❌ エラーが発生しました: {error_msg}")
        messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{error_msg}")


def main():
    """Main entry point for GUI application"""
    app = ManualProcessorGUI()
    app.mainloop()


if __name__ == "__main__":
    main()