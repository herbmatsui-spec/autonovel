from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.backend.auth import require_api_key
from src.models.publishing_assistant import TargetPlatform, FormattedChapterPayload
from src.services.publishing.content_splitter import ContentSplitter
from src.services.publishing.ai_disclosure_generator import AIDisclosureGenerator
from src.services.publishing.compliance_validator import ComplianceValidator

router = APIRouter(
    prefix="/publishing-assistant",
    tags=["publishing_assistant"],
)

class FormatRequest(BaseModel):
    platform: TargetPlatform = Field(TargetPlatform.KAKUYOMU, description="投稿先プラットフォーム")
    chapter_title: str = Field(..., description="話・章のタイトル")
    raw_text: str = Field(..., description="元の生成テキスト（マーカーやルビ含む）")
    ai_role: str = Field("assisted", description="AI利用役割")


@router.post("/format", response_model=FormattedChapterPayload)
async def format_chapter_for_publishing(request: FormatRequest, api_key: str = Depends(require_api_key)):
    """小説テキストをプラットフォーム別（カクヨム・なろう等）に分割・整形し、
    AI開示文言および規約バリデーション結果を返却する。
    """
    try:
        # 1. 前書き・本文・後書きの自動分割
        split_result = ContentSplitter.split_chapter_content(request.raw_text)
        foreword = split_result["foreword"]
        main_content = split_result["main_content"]
        afterword = split_result["afterword"]

        # 2. ルビ記法のプラットフォーム別変換
        platform_str = request.platform.value
        foreword = ContentSplitter.convert_ruby(foreword, platform_str)
        main_content = ContentSplitter.convert_ruby(main_content, platform_str)
        afterword = ContentSplitter.convert_ruby(afterword, platform_str)

        # 3. AI開示文言の生成
        ai_statement = AIDisclosureGenerator.generate_disclosure(request.platform, request.ai_role)

        # もし後書きにAI開示文が含まれていなければ追記
        if ai_statement not in afterword:
            if afterword:
                afterword = f"{afterword}\n\n{ai_statement}"
            else:
                afterword = ai_statement

        # 4. 総文字数計算
        total_chars = len(foreword) + len(main_content) + len(afterword)

        # 5. 規約事前バリデーション
        warnings = ComplianceValidator.validate_chapter(
            platform=request.platform,
            chapter_title=request.chapter_title,
            main_content=main_content,
            foreword=foreword,
            afterword=afterword
        )

        return FormattedChapterPayload(
            platform=request.platform,
            chapter_title=request.chapter_title,
            foreword=foreword,
            main_content=main_content,
            afterword=afterword,
            char_count=total_chars,
            ai_disclosure_statement=ai_statement,
            validation_warnings=warnings
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Publishing assistant formatting failed: {str(e)}")
