import os
import threading
from pathlib import Path
from typing import Dict, Optional


class PromptLoader:
    """
    プロンプトテンプレートをロードし、変数を置換するローダー。
    バージョン指定、フォールバック、キャッシュ機能を提供。
    """

    def __init__(self, base_path: Optional[str] = None):
        """
        プロンプトローダーを初期化。
        
        Args:
            base_path: プロンプトファイルのベースディレクトリ。
                      Noneの場合は、このファイルの親ディレクトリの親の「prompts」を使用。
        """
        if base_path is None:
            # このファイルの場所から推測: src/prompts/loader.py -> src/prompts -> src -> プロジェクトルート
            # そしてプロジェクトルートの prompts ディレクトリ
            current_file = Path(__file__).resolve()
            self.base_path = current_file.parent.parent.parent / "prompts"
        else:
            self.base_path = Path(base_path)
        
        # キャッシュ: {(template_name, version): template_string}
        self._cache: Dict[tuple, str] = {}
        self._cache_lock = threading.Lock()
        
        # 利用可能なバージョンを検出
        self._available_versions = self._detect_versions()
    
    def _detect_versions(self) -> list:
        """利用可能なバージョンディレクトリを検出"""
        versions = []
        if self.base_path.exists():
            for item in self.base_path.iterdir():
                if item.is_dir() and item.name not in ["base", "latest"]:
                    versions.append(item.name)
        # ベースとlatestは常に利用可能とみなす
        if (self.base_path / "base").exists():
            versions.append("base")
        if (self.base_path / "latest").exists():
            versions.append("latest")
        return sorted(list(set(versions)))
    
    def _get_template_path(self, template_name: str, version: str) -> Path:
        """テンプレートファイルのフルパスを取得"""
        return self.base_path / version / f"{template_name}.yaml"
    
    def load(self, template_name: str, version: str = "latest") -> str:
        """
        テンプレートをロードし、生の文字列を返す（変数は置換しない）。
        
        Args:
            template_name: テンプレート名（拡張子なし、例: "system"）
            version: バージョン名（デフォルト: "latest"）
            
        Returns:
            テンプレートの生の文字列
            
        Raises:
            FileNotFoundError: テンプレートが見つからない場合
        """
        # フォールバックロジック: 指定バージョン → base → 最初の利用可能バージョン
        fallback_versions = [version, "base"] + [v for v in self._available_versions if v not in [version, "base"]]
        
        for ver in fallback_versions:
            cache_key = (template_name, ver)
            with self._cache_lock:
                if cache_key in self._cache:
                    return self._cache[cache_key]
            
            template_path = self._get_template_path(template_name, ver)
            if template_path.exists():
                with open(template_path, "r", encoding="utf-8") as f:
                    content = f.read()
                with self._cache_lock:
                    self._cache[cache_key] = content
                return content
        
        raise FileNotFoundError(
            f"テンプレートが見つかりません: {template_name}.yaml "
            f"(バージョン: {version}, 試したバージョン: {fallback_versions})"
        )
    
    def render(self, template_name: str, version: str = "latest", **variables) -> str:
        """
        テンプレートをロードし、変数を置換して返す。
        
        Args:
            template_name: テンプレート名（拡張子なし）
            version: バージョン名（デフォルト: "latest"）
            **variables: テンプレート内の{変数}を置換するためのキーワード引数
            
        Returns:
            変数が置換されたレンダリング済み文字列
        """
        template = self.load(template_name, version)
        # 簡単な変数置換: {key} を variables[key] で置換
        rendered = template
        for key, value in variables.items():
            rendered = rendered.replace("{" + key + "}", str(value))
        return rendered


# シングルトンインスタンス（オプション）
default_loader = PromptLoader()


if __name__ == "__main__":
    # 簡単な動作テスト
    loader = PromptLoader()
    print("利用可能なバージョン:", loader._available_versions)
    
    # システムプロンプトをロード
    system_prompt = loader.load("system")
    print("\n--- システムプロンプト (raw) ---")
    print(system_prompt[:200] + "..." if len(system_prompt) > 200 else system_prompt)
    
    # レンダリングテスト
    rendered = loader.render(
        "system",
        version="v1.0",
        min_chars=1000,
        max_chars=5000,
        genre="ファンタジー",
        keywords=["ドラゴン", "魔法"],
        tone="壮大"
    )
    print("\n--- レンダリング結果 ---")
    print(rendered)