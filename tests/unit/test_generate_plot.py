#!/usr/bin/env python3
"""
tests/unit/test_generate_plot.py

generate_plot.py の単体テスト・統合テスト
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from scripts.generate_plot import (
    GenreProfile,
    PlotGenerationInput,
    PlotGenerationOutput,
    _format_plot_as_markdown,
    _heuristic_parse_fallback,
    apply_genre_constraints,
    build_arg_parser,
    build_prompt_variables,
    call_llm_for_plot,
    get_genre_config,
    get_genre_profile,
    load_genre_config,
    load_novelize_template,
    parse_keywords,
    parse_llm_plot_response,
    render_novelize_prompt,
    run_generate_plot,
    save_plot_output,
    select_keywords_for_genre,
    validate_generated_plot,
)

# =============================================================================
# テストフィクスチャ
# =============================================================================


@pytest.fixture
def sample_genre_config():
    """テスト用のジャンル設定サンプル"""
    return {
        "genres": {
            "light": {
                "name": "LIGHT",
                "description": "癒やし・スローライフ",
                "evaluation_axes": ["癒やし度", "語彙の平易さ"],
                "constraint_profile": "死や過度な流血描写の禁止",
                "keywords": ["ほのぼの", "スローライフ", "日常", "カフェ", "料理"],
            },
            "standard": {
                "name": "STANDARD",
                "description": "王道ファンタジー",
                "evaluation_axes": ["王道感", "成長の爽快感"],
                "constraint_profile": "",
                "keywords": ["冒険", "魔法", "剣", "ドラゴン", "成り上がり"],
            },
            "dark": {
                "name": "DARK",
                "description": "ダーク・復讐",
                "evaluation_axes": ["絶望感", "カタルシス"],
                "constraint_profile": "安易な救済の禁止。カタルシスには犠牲を伴うこと",
                "keywords": ["復讐", "ダーク", "ホラー", "狂気", "鬱"],
            },
            "psychological_horror": {
                "name": "PSYCHOLOGICAL_HORROR",
                "description": "サイコロジカルホラー",
                "evaluation_axes": ["不気味さ", "精神的負荷"],
                "constraint_profile": "物理的解決封殺。精神汚染・喪失を必須とする",
                "keywords": ["サイコロジカル", "狂気", "記憶喪失", "存在希薄"],
            },
        }
    }


@pytest.fixture
def temp_project_dir(sample_genre_config):
    """テスト用の統合プロジェクトディレクトリを作成（config/data と prompts/templates/utility の両方を含む）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # config/data/genres.json
        genres_dir = tmpdir_path / "config" / "data"
        genres_dir.mkdir(parents=True, exist_ok=True)
        genres_file = genres_dir / "genres.json"
        with open(genres_file, "w", encoding="utf-8") as f:
            json.dump(sample_genre_config, f, ensure_ascii=False)

        # prompts/templates/utility/novelize_prompt.j2
        template_dir = tmpdir_path / "prompts" / "templates" / "utility"
        template_dir.mkdir(parents=True, exist_ok=True)
        template_path = template_dir / "novelize_prompt.j2"
        template_content = """[SYSTEM]
あなたは極上の文体を持つWeb小説家です。
以下の【台本】を骨格とし、最高密度の小説を執筆してください。

【Target Style & Rules】
{{ style_instruction }}
{{ rule_set_content }}
[/SYSTEM]

{{ plots_text }}
{{ scripts_text }}

【Character Context】
{{ char_context }}

【Previous Context】
{{ prev_context }}"""
        template_path.write_text(template_content, encoding="utf-8")

        yield tmpdir_path


@pytest.fixture
def sample_input_params():
    """テスト用の入力パラメータ"""
    return PlotGenerationInput(
        genre="standard",
        seed_keywords=["冒険", "魔法"],
        target_length=3000,
        style_key="style_web_standard",
        write_rule_type="RULE_SET_A",
        extra_context="",
        target_episodes=1,
        temperature=0.8,
        max_tokens=4000,
    )


@pytest.fixture
def sample_genre_profile():
    """テスト用のジャンルプロファイル"""
    return GenreProfile(
        name="STANDARD",
        description="王道ファンタジー",
        evaluation_axes=["王道感", "成長の爽快感"],
        constraint_profile="",
        keywords=["冒険", "魔法", "剣", "ドラゴン"],
    )


@pytest.fixture
def mock_llm_response():
    """モックLLMレスポンス"""
    return """```json
{
  "title": "テストタイトル",
  "logline": "テストログライン",
  "synopsis": "これはテスト用のあらすじです。十分な長さがあります。主人公が冒険に出て、魔法を使って敵を倒し、成長していく物語です。",
  "beats": ["導入: 主人公の日常", "発端: 事件発生", "展開: 冒険の始まり", "転換: 試練と成長", "結末: 勝利と新たな旅立ち"],
  "characters": [
    {"name": "主人公", "role": "main", "description": "勇敢な冒険者"},
    {"name": "師匠", "role": "support", "description": "主人公を導く賢者"}
  ],
  "genre_metadata": {"genre": "standard"}
}
```"""


@pytest.fixture
def mock_llm_response_incomplete():
    """不完全なモックLLMレスポンス（ヒューリスティックパース用）"""
    return """タイトル: 不完全なプロット
ログライン: テスト
あらすじ: これは不完全なレスポンスです。
- ビート1
- ビート2
- ビート3"""


# =============================================================================
# モッククラス
# =============================================================================


class MockLLMClient:
    """テスト用のモックLLMクライアント"""

    def __init__(self, response: str = None, should_fail: bool = False):
        self.response = response or """```json
{
  "title": "モックタイトル",
  "logline": "モックログライン",
  "synopsis": "モックあらすじ。十分な長さがあります。主人公が冒険して成長する話です。",
  "beats": ["ビート1", "ビート2", "ビート3", "ビート4"],
  "characters": [{"name": "主人公", "role": "main", "description": "説明"}],
  "genre_metadata": {"genre": "standard"}
}
```"""
        self.should_fail = should_fail
        self.call_count = 0
        self.last_prompt = None

    async def generate(self, prompt: str, temperature: float = 0.8, max_tokens: int = 4000) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        if self.should_fail:
            raise RuntimeError("LLM generation failed")
        return self.response


# =============================================================================
# 単体テスト: 設定読み込み
# =============================================================================


class TestLoadGenreConfig:
    """load_genre_config のテスト"""

    def test_load_genre_config_success(self, temp_project_dir):
        """正常にジャンル設定が読み込まれること"""
        import scripts.generate_plot as gp
        original_base_dir = gp.BASE_DIR
        gp.BASE_DIR = temp_project_dir

        try:
            config = load_genre_config()
            assert "light" in config
            assert "standard" in config
            assert "dark" in config
            assert "psychological_horror" in config

            assert config["light"].name == "LIGHT"
            assert config["standard"].name == "STANDARD"
            assert len(config["light"].keywords) == 5
            assert len(config["standard"].keywords) == 5
        finally:
            gp.BASE_DIR = original_base_dir

    def test_load_genre_config_caching(self, temp_project_dir):
        """キャッシュが機能すること"""
        import scripts.generate_plot as gp
        original_base_dir = gp.BASE_DIR
        gp.BASE_DIR = temp_project_dir

        try:
            config1 = get_genre_config()
            config2 = get_genre_config()
            assert config1 is config2
        finally:
            gp.BASE_DIR = original_base_dir


class TestLoadNovelizeTemplate:
    """load_novelize_template のテスト"""

    def test_load_novelize_template_success(self, temp_project_dir):
        """正常にテンプレートが読み込まれること"""
        import scripts.generate_plot as gp
        original_base_dir = gp.BASE_DIR
        gp.BASE_DIR = temp_project_dir

        try:
            template = load_novelize_template()
            assert template is not None
            template2 = load_novelize_template()
            assert template is template2
        finally:
            gp.BASE_DIR = original_base_dir


class TestGetGenreProfile:
    """get_genre_profile のテスト"""

    def test_get_genre_profile_exists(self, temp_project_dir):
        """存在するジャンルが取得できること"""
        import scripts.generate_plot as gp
        original_base_dir = gp.BASE_DIR
        gp.BASE_DIR = temp_project_dir

        try:
            profile = get_genre_profile("light")
            assert profile.name == "LIGHT"
            assert "癒やし度" in profile.evaluation_axes
        finally:
            gp.BASE_DIR = original_base_dir

    def test_get_genre_profile_fallback(self, temp_project_dir):
        """存在しないジャンルは standard にフォールバックすること"""
        import scripts.generate_plot as gp
        original_base_dir = gp.BASE_DIR
        gp.BASE_DIR = temp_project_dir

        try:
            profile = get_genre_profile("nonexistent")
            assert profile.name == "STANDARD"
        finally:
            gp.BASE_DIR = original_base_dir


# =============================================================================
# 単体テスト: キーワード選択
# =============================================================================


class TestSelectKeywordsForGenre:
    """select_keywords_for_genre のテスト"""

    def test_select_keywords_user_priority(self, temp_project_dir):
        """ユーザー指定キーワードが優先されること"""
        import scripts.generate_plot as gp
        original_base_dir = gp.BASE_DIR
        gp.BASE_DIR = temp_project_dir

        try:
            selected = select_keywords_for_genre("light", count=3, user_keywords=["ほのぼのぼの", "カフェ"])
            assert "ほのぼの" in selected
            assert "カフェ" in selected
            assert len(selected) == 3
        finally:
            gp.BASE_DIR = original_base_dir

    def test_select_keywords_random_fill(self, temp_project_dir):
        """不足分がランダムに補填されること"""
        import scripts.generate_plot as gp
        original_base_dir = gp.BASE_DIR
        gp.BASE_DIR = temp_project_dir

        try:
            selected = select_keywords_for_genre("light", count=5, user_keywords=["ほのぼの"])
            assert "ほのぼの" in selected
            assert len(selected) == 5
        finally:
            gp.BASE_DIR = original_base_dir

    def test_select_keywords_no_user_keywords(self, temp_project_dir):
        """ユーザーキーワードなしでも動作すること"""
        import scripts.generate_plot as gp
        original_base_dir = gp.BASE_DIR
        gp.BASE_DIR = temp_project_dir

        try:
            selected = select_keywords_for_genre("dark", count=3)
            assert len(selected) == 3
            assert all(kw in ["復讐", "ダーク", "ホラー", "狂気", "鬱"] for kw in selected)
        finally:
            gp.BASE_DIR = original_base_dir


# =============================================================================
# 単体テスト: プロンプト変数構築
# =============================================================================


class TestBuildPromptVariables:
    """build_prompt_variables のテスト"""

    def test_build_prompt_variables_basic(self, sample_input_params, sample_genre_profile):
        """基本的な変数構築が正常に動作すること"""
        variables = build_prompt_variables(
            input_params=sample_input_params,
            genre_profile=sample_genre_profile,
            selected_keywords=["冒険", "魔法"],
        )

        assert "style_instruction" in variables
        assert "rule_set_content" in variables
        assert "plots_text" in variables
        assert "scripts_text" in variables
        assert "char_context" in variables
        assert "prev_context" in variables

        assert "STANDARD" in variables["style_instruction"]
        assert "冒険" in variables["plots_text"]
        assert "魔法" in variables["plots_text"]

    def test_build_prompt_variables_with_custom_values(self, sample_input_params, sample_genre_profile):
        """カスタム値が正しく反映されること"""
        variables = build_prompt_variables(
            input_params=sample_input_params,
            genre_profile=sample_genre_profile,
            selected_keywords=["冒険"],
            style_instruction="カスタムスタイル",
            rule_set_content="カスタムルール",
            plots_text="カスタムプロット",
            scripts_text="カスタムスクリプト",
            char_context="カスタムキャラ",
            prev_context="カスタム前文脈",
        )

        assert variables["style_instruction"] == "カスタムスタイル"
        assert variables["rule_set_content"] == "カスタムルール"
        assert variables["plots_text"] == "カスタムプロット"
        assert variables["scripts_text"] == "カスタムスクリプト"
        assert variables["char_context"] == "カスタムキャラ"
        assert variables["prev_context"] == "カスタム前文脈"


# =============================================================================
# 単体テスト: テンプレートレンダリング
# =============================================================================


class TestRenderNovelizePrompt:
    """render_novelize_prompt のテスト"""

    def test_render_novelize_prompt(self, temp_project_dir):
        """テンプレートが正しくレンダリングされること"""
        import scripts.generate_plot as gp
        original_base_dir = gp.BASE_DIR
        gp.BASE_DIR = temp_project_dir

        try:
            template = load_novelize_template()
            variables = {
                "style_instruction": "テストスタイル",
                "rule_set_content": "テストルール",
                "plots_text": "テストプロット",
                "scripts_text": "テストスクリプト",
                "char_context": "テストキャラ",
                "prev_context": "テスト前文脈",
            }
            rendered = render_novelize_prompt(template, variables)

            assert "テストスタイル" in rendered
            assert "テストルール" in rendered
            assert "テストプロット" in rendered
            assert "テストスクリプト" in rendered
            assert "テストキャラ" in rendered
            assert "テスト前文脈" in rendered
        finally:
            gp.BASE_DIR = original_base_dir


# =============================================================================
# 単体テスト: LLM呼び出し（モック）
# =============================================================================


class TestCallLLMForPlot:
    """call_llm_for_plot のテスト"""

    @pytest.mark.asyncio
    async def test_call_llm_for_plot_mock(self):
        """モックLLM呼び出しが動作すること"""
        result = await call_llm_for_plot("test prompt", temperature=0.8, max_tokens=4000)

        assert isinstance(result, str)
        assert "title" in result
        assert "logline" in result
        assert "synopsis" in result
        assert "beats" in result
        assert "characters" in result


# =============================================================================
# 単体テスト: レスポンスパース
# =============================================================================


class TestParseLLMPlotResponse:
    """parse_llm_plot_response のテスト"""

    def test_parse_valid_json_response(self, mock_llm_response):
        """有効なJSONレスポンスが正しくパースされること"""
        output = parse_llm_plot_response(mock_llm_response)

        assert isinstance(output, PlotGenerationOutput)
        assert output.title == "テストタイトル"
        assert output.logline == "テストログライン"
        assert "テスト用のあらすじ" in output.synopsis
        assert len(output.beats) == 5
        assert len(output.characters) == 2
        assert output.characters[0]["name"] == "主人公"

    def test_parse_json_without_code_block(self):
        """コードブロックなしのJSONもパースできること"""
        json_str = json.dumps({
            "title": "ノーコードブロック",
            "logline": "ログライン",
            "synopsis": "あらすじテキスト。十分な長さがあります。",
            "beats": ["ビート1", "ビート2", "ビート3"],
            "characters": [],
            "genre_metadata": {}
        })

        output = parse_llm_plot_response(json_str)
        assert output.title == "ノーコードブロック"

    def test_heuristic_fallback(self, mock_llm_response_incomplete):
        """JSONパース失敗時のヒューリスティックフォールバック"""
        output = parse_llm_plot_response(mock_llm_response_incomplete)

        assert isinstance(output, PlotGenerationOutput)
        assert output.genre_metadata.get("parse_method") == "heuristic_fallback"


class TestHeuristicParseFallback:
    """_heuristic_parse_fallback のテスト"""

    def test_heuristic_parse_extracts_title(self):
        """タイトルが抽出されること"""
        text = "タイトル: 抽出されたタイトル\nログライン: テスト\nあらすじ: テストあらすじ"
        output = _heuristic_parse_fallback(text)
        assert "抽出されたタイトル" in output.title

    def test_heuristic_parse_extracts_beats(self):
        """ビートが抽出されること"""
        text = """タイトル: テスト
- ビート1
- ビート2
・ビート3
* ビート4"""
        output = _heuristic_parse_fallback(text)
        assert len(output.beats) >= 3


# =============================================================================
# 単体テスト: バリデーション
# =============================================================================


class TestValidateGeneratedPlot:
    """validate_generated_plot のテスト"""

    def test_validate_valid_plot(self):
        """有効なプロットはパスすること"""
        output = PlotGenerationOutput(
            title="有効なタイトル",
            logline="有効なログライン",
            synopsis="これは十分な長さのあらすじです。主人公が冒険して成長していく物語で、非常に面白い展開になります。" * 2,
            beats=["ビート1", "ビート2", "ビート3", "ビート4"],
            characters=[{"name": "主人公", "role": "main"}],
        )

        assert validate_generated_plot(output) is True

    def test_validate_empty_title_fails(self):
        """空タイトルは失敗すること"""
        output = PlotGenerationOutput(
            title="",
            logline="ログライン",
            synopsis="あらすじ" * 20,
            beats=["1", "2", "3"],
        )

        with pytest.raises(ValueError, match="title is empty"):
            validate_generated_plot(output)

    def test_validate_empty_logline_fails(self):
        """空ログラインは失敗すること"""
        output = PlotGenerationOutput(
            title="タイトル",
            logline="",
            synopsis="あらすじ" * 20,
            beats=["1", "2", "3"],
        )

        with pytest.raises(ValueError, match="logline is empty"):
            validate_generated_plot(output)

    def test_validate_short_synopsis_fails(self):
        """短すぎるあらすじは失敗すること"""
        output = PlotGenerationOutput(
            title="タイトル",
            logline="ログライン",
            synopsis="短い",
            beats=["1", "2", "3"],
        )

        with pytest.raises(ValueError, match="synopsis too short"):
            validate_generated_plot(output)

    def test_validate_long_synopsis_fails(self):
        """長すぎるあらすじは失敗すること"""
        output = PlotGenerationOutput(
            title="タイトル",
            logline="ログライン",
            synopsis="あ" * 15000,
            beats=["1", "2", "3"],
        )

        with pytest.raises(ValueError, match="synopsis too long"):
            validate_generated_plot(output)

    def test_validate_few_beats_fails(self):
        """ビートが少なすぎる場合は失敗すること"""
        output = PlotGenerationOutput(
            title="タイトル",
            logline="ログライン",
            synopsis="あらすじ" * 20,
            beats=["1", "2"],
        )

        with pytest.raises(ValueError, match="too few beats"):
            validate_generated_plot(output)

    def test_validate_many_beats_fails(self):
        """ビートが多すぎる場合は失敗すること"""
        output = PlotGenerationOutput(
            title="タイトル",
            logline="ログライン",
            synopsis="あらすじ" * 20,
            beats=[f"ビート{i}" for i in range(25)],
        )

        with pytest.raises(ValueError, match="too many beats"):
            validate_generated_plot(output)


# =============================================================================
# 単体テスト: ジャンル制約適用
# =============================================================================


class TestApplyGenreConstraints:
    """apply_genre_constraints のテスト"""

    def test_apply_constraints_light_genre(self):
        """lightジャンルの制約が適用されること"""
        output = PlotGenerationOutput(
            title="テスト",
            logline="テスト",
            synopsis="あらす" * 20,
            beats=["1", "2", "3"],
        )

        profile = GenreProfile(
            name="LIGHT",
            description="癒やし",
            evaluation_axes=[],
            constraint_profile="死や過度な流血描写の禁止",
            keywords=[],
        )

        result = apply_genre_constraints(output, profile)

        assert result.genre_metadata["applied_constraints"] == "死や過度な流血描写の禁止"
        assert result.genre_metadata["has_strict_constraints"] is True

    def test_apply_constraints_dark_genre(self):
        """darkジャンルの制約が適用されること"""
        output = PlotGenerationOutput(
            title="テスト",
            logline="テスト",
            synopsis="あらすじ" * 20,
            beats=["1", "2", "3"],
        )

        profile = GenreProfile(
            name="DARK",
            description="ダーク",
            evaluation_axes=[],
            constraint_profile="安易な救済の禁止。カタルシスには必ず犠牲を伴うこと",
            keywords=[],
        )

        result = apply_genre_constraints(output, profile)

        assert result.genre_metadata["requires_catharsis"] is True

    def test_apply_constraints_empty_profile(self):
        """制約プロファイルが空の場合はそのまま返されること"""
        output = PlotGenerationOutput(
            title="テスト",
            logline="テスト",
            synopsis="あらすじ" * 20,
            beats=["1", "2", "3"],
        )

        profile = GenreProfile(
            name="STANDARD",
            description="標準",
            evaluation_axes=[],
            constraint_profile="",
            keywords=[],
        )

        result = apply_genre_constraints(output, profile)
        assert result is output


# =============================================================================
# 単体テスト: 保存機能
# =============================================================================


class TestSavePlotOutput:
    """save_plot_output のテスト"""

    def test_save_json_format(self, tmp_path):
        """JSON形式で保存できること"""
        output = PlotGenerationOutput(
            title="保存テスト",
            logline="ログライン",
            synopsis="あらすじ" * 20,
            beats=["1", "2", "3"],
            characters=[{"name": "主人公", "role": "main"}],
            genre_metadata={"genre": "standard"},
        )

        saved_path = save_plot_output(output, tmp_path, fmt="json")

        assert saved_path.exists()
        assert saved_path.suffix == ".json"

        with open(saved_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["title"] == "保存テスト"
        assert data["genre_metadata"]["genre"] == "standard"

    def test_save_markdown_format(self, tmp_path):
        """Markdown形式で保存できること"""
        output = PlotGenerationOutput(
            title="マークダウンテスト",
            logline="ログライン",
            synopsis="あらすじ" * 20,
            beats=["ビート1", "ビート2"],
            characters=[{"name": "主人公", "role": "main", "description": "説明"}],
            genre_metadata={"genre": "light"},
        )

        saved_path = save_plot_output(output, tmp_path, fmt="md")

        assert saved_path.exists()
        assert saved_path.suffix == ".md"

        content = saved_path.read_text(encoding="utf-8")
        assert "# マークダウンテスト" in content
        assert "**Logline**: ログライン" in content
        assert "## あらすじ" in content
        assert "## ビート" in content
        assert "## 登場人物" in content
        assert "主人公" in content

    def test_save_invalid_format_raises(self, tmp_path):
        """無効な形式はエラーになること"""
        output = PlotGenerationOutput(
            title="テスト",
            logline="テスト",
            synopsis="あらすじ" * 20,
            beats=["1", "2", "3"],
        )

        with pytest.raises(ValueError, match="Unsupported format"):
            save_plot_output(output, tmp_path, fmt="xml")


class TestFormatPlotAsMarkdown:
    """_format_plot_as_markdown のテスト"""

    def test_format_basic(self):
        """基本的なフォーマットが正しいこと"""
        output = PlotGenerationOutput(
            title="テストタイトル",
            logline="テストログライン",
            synopsis="テストあらすじ",
            beats=["ビート1", "ビート2"],
            characters=[{"name": "キャラ1", "role": "main", "description": "説明1"}],
            genre_metadata={"genre": "standard", "custom_key": "custom_value"},
        )

        md = _format_plot_as_markdown(output)

        assert "# テストタイトル" in md
        assert "**Logline**: テストログライン" in md
        assert "## あらすじ" in md
        assert "テストあらすじ" in md
        assert "## ビート" in md
        assert "1. ビート1" in md
        assert "2. ビート2" in md
        assert "## 登場人物" in md
        assert "**キャラ1** (main): 説明1" in md
        assert "## ジャンルメタデータ" in md
        assert "**genre**: standard" in md
        assert "**custom_key**: custom_value" in md


# =============================================================================
# 単体テスト: CLI引数パース
# =============================================================================


class TestParseKeywords:
    """parse_keywords のテスト"""

    def test_parse_comma_separated(self):
        """カンマ区切りが正しくパースされること"""
        result = parse_keywords("キーワード1, キーワード2,キーワード3")
        assert result == ["キーワード1", "キーワード2", "キーワード3"]

    def test_parse_empty_string(self):
        """空文字列は空リストになること"""
        result = parse_keywords("")
        assert result == []

    def test_parse_none(self):
        """Noneは空リストになること"""
        result = parse_keywords(None)
        assert result == []


class TestBuildArgParser:
    """build_arg_parser のテスト"""

    def test_parser_defaults(self):
        """デフォルト値が正しく設定されること"""
        parser = build_arg_parser()
        args = parser.parse_args([])

        assert args.genre == "standard"
        assert args.keywords == ""
        assert args.count == 1
        assert args.output_dir == "outputs/plots"
        assert args.format == "json"
        assert args.target_length == 3000
        assert args.temperature == 0.8
        assert args.max_tokens == 4000

    def test_parser_custom_args(self):
        """カスタム引数が正しくパースされること"""
        parser = build_arg_parser()
        args = parser.parse_args([
            "--genre", "light",
            "--keywords", "ほのぼの,カフェ",
            "--count", "3",
            "--output-dir", "./custom/output",
            "--format", "md",
            "--target-length", "5000",
            "--temperature", "0.9",
            "--max-tokens", "6000",
            "--verbose",
            "--dry-run",
        ])

        assert args.genre == "light"
        assert args.keywords == "ほのぼの,カフェ"
        assert args.count == 3
        assert args.output_dir == "./custom/output"
        assert args.format == "md"
        assert args.target_length == 5000
        assert args.temperature == 0.9
        assert args.max_tokens == 6000
        assert args.verbose is True
        assert args.dry_run is True

    def test_parser_invalid_genre(self):
        """無効なジャンルはエラーになること"""
        parser = build_arg_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--genre", "invalid_genre"])


# =============================================================================
# 統合テスト: run_generate_plot
# =============================================================================


class TestRunGeneratePlotIntegration:
    """run_generate_plot 統合テスト"""

    @pytest.mark.asyncio
    async def test_run_generate_plot_dry_run(self, temp_project_dir, sample_input_params):
        """ドライランモードでプロンプトが生成されること"""
        import scripts.generate_plot as gp
        original_base_dir = gp.BASE_DIR
        gp.BASE_DIR = temp_project_dir

        try:
            with patch.object(gp, 'call_llm_for_plot', new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = """```json
{
  "title": "統合テストタイトル",
  "logline": "統合テストログライン",
  "synopsis": "統合テスト用のあらすじです。十分な長さがあります。主人公が冒険して成長します。",
  "beats": ["ビート1", "ビート2", "ビート3", "ビート4"],
  "characters": [{"name": "主人公", "role": "main", "description": "説明"}],
  "genre_metadata": {}
}
```"""

                output = await run_generate_plot(sample_input_params)

                assert output.title == "統合テストタイトル"
                assert len(output.beats) == 4
                mock_llm.assert_called_once()
        finally:
            gp.BASE_DIR = original_base_dir

    @pytest.mark.asyncio
    async def test_run_generate_plot_with_constraints(self, temp_project_dir):
        """ジャンル制約が適用されること"""
        import scripts.generate_plot as gp
        original_base_dir = gp.BASE_DIR
        gp.BASE_DIR = temp_project_dir

        try:
            input_params = PlotGenerationInput(
                genre="dark",
                seed_keywords=["復讐"],
                target_length=3000,
            )

            with patch.object(gp, 'call_llm_for_plot', new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = """```json
{
  "title": "ダークテスト",
  "logline": "復讐の物語",
  "synopsis": "主人公が復讐のために闇に堕ちていくダークな物語です。十分な長さのあらすじテキストです。",
  "beats": ["導入", "復讐の決意", "闇への堕落", "対決", "結末"],
  "characters": [],
  "genre_metadata": {}
}
```"""

                output = await run_generate_plot(input_params)

                assert output.genre_metadata["genre"] == "dark"
                assert "requires_catharsis" in output.genre_metadata
                assert output.genre_metadata["requires_catharsis"] is True
        finally:
            gp.BASE_DIR = original_base_dir


# =============================================================================
# 統合テスト: CLI
# =============================================================================


class TestCLIIntegration:
    """CLI統合テスト"""

    @pytest.mark.asyncio
    async def test_cli_dry_run(self, temp_project_dir, tmp_path, capsys):
        """CLIドライランが動作すること"""
        import scripts.generate_plot as gp
        original_base_dir = gp.BASE_DIR
        gp.BASE_DIR = temp_project_dir

        try:
            parser = build_arg_parser()
            args = parser.parse_args([
                "--genre", "light",
                "--keywords", "ほのぼの,カフェ",
                "--count", "2",
                "--output-dir", str(tmp_path),
                "--format", "json",
                "--dry-run",
                "--verbose",
            ])

            results = await gp.run_cli_generation(args)

            assert results == []

            captured = capsys.readouterr()
            assert "DRY RUN" in captured.out
        finally:
            gp.BASE_DIR = original_base_dir

    @pytest.mark.asyncio
    async def test_cli_actual_generation(self, temp_project_dir, tmp_path):
        """CLI実際の生成が動作すること"""
        import scripts.generate_plot as gp
        original_base_dir = gp.BASE_DIR
        gp.BASE_DIR = temp_project_dir

        try:
            parser = build_arg_parser()
            args = parser.parse_args([
                "--genre", "standard",
                "--count", "1",
                "--output-dir", str(tmp_path),
                "--format", "json",
            ])

            with patch.object(gp, 'call_llm_for_plot', new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = """```json
{
  "title": "CLIテストタイトル",
  "logline": "CLIテストログライン",
  "synopsis": "CLI統合テスト用のあらすじです。主人公が冒険して魔法を習得し、世界を救う物語です。",
  "beats": ["日常", "冒険の始まり", "試練", "成長", "勝利"],
  "characters": [{"name": "主人公", "role": "main", "description": "勇者"}],
  "genre_metadata": {}
}
```"""

                results = await gp.run_cli_generation(args)

                assert len(results) == 1
                assert results[0].title == "CLIテストタイトル"

                json_files = list(tmp_path.glob("*.json"))
                assert len(json_files) == 1
        finally:
            gp.BASE_DIR = original_base_dir


# =============================================================================
# ジャンル別生成テスト
# =============================================================================


class TestGenreSpecificGeneration:
    """ジャンル別生成テスト"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("genre", ["light", "standard", "dark", "psychological_horror"])
    async def test_each_genre_generation(self, genre, temp_project_dir):
        """各ジャンルで生成が動作すること"""
        import scripts.generate_plot as gp
        original_base_dir = gp.BASE_DIR
        gp.BASE_DIR = temp_project_dir

        try:
            input_params = PlotGenerationInput(genre=genre)

            with patch.object(gp, 'call_llm_for_plot', new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = f'''```json
{{
  "title": "{genre}タイトル",
  "logline": "{genre}ログライン",
  "synopsis": "{genre}ジャンルのあらすじです。十分な長さがあります。特徴的な展開が含まれます。",
  "beats": ["ビート1", "ビート2", "ビート3", "ビート4"],
  "characters": [],
  "genre_metadata": {{"genre": "{genre}"}}
}}
```'''

                output = await run_generate_plot(input_params)

                assert output.genre_metadata["genre"] == genre
                assert output.title == f"{genre}タイトル"
        finally:
            gp.BASE_DIR = original_base_dir


# =============================================================================
# データモデルテスト
# =============================================================================


class TestDataModels:
    """データモデルのテスト"""

    def test_plot_generation_input_validation(self):
        """PlotGenerationInput のバリデーション"""
        input_params = PlotGenerationInput(genre="light")
        assert input_params.genre == "light"

        with pytest.raises(ValueError, match="Invalid genre"):
            PlotGenerationInput(genre="invalid")

    def test_plot_generation_input_defaults(self):
        """デフォルト値が正しく設定されること"""
        input_params = PlotGenerationInput()

        assert input_params.genre == "standard"
        assert input_params.seed_keywords == []
        assert input_params.target_length == 3000
        assert input_params.style_key == "style_web_standard"
        assert input_params.write_rule_type == "RULE_SET_A"
        assert input_params.temperature == 0.8
        assert input_params.max_tokens == 4000

    def test_plot_generation_output_creation(self):
        """PlotGenerationOutput の作成"""
        output = PlotGenerationOutput(
            title="テスト",
            logline="ログ",
            synopsis="あらすじ",
        )

        assert output.title == "テスト"
        assert output.created_at is not None

    def test_genre_profile_creation(self):
        """GenreProfile の作成"""
        profile = GenreProfile(
            name="TEST",
            description="テスト",
            evaluation_axes=["軸1", "軸2"],
            constraint_profile="制約",
            keywords=["キーワード1", "キーワード2"],
        )

        assert profile.name == "TEST"
        assert len(profile.evaluation_axes) == 2
        assert len(profile.keywords) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
