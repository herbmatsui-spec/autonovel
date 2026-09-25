"""
Social reaction generation service for streaming comments and forum posts.
PLAN 02: エンタメ演出強化・マルチジャンル＆配信・掲示板演出
"""
from __future__ import annotations

import json
import logging
from typing import List, Union
from src.services.llm_service import LLMService
from src.models.social_reaction import StreamComment, ForumPost

logger = logging.getLogger(__name__)


class SocialReactionGenerator:
    """本文のハイライトに応じた演出ブロック生成器"""

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def generate_stream_comments(
        self, 
        highlight_description: str, 
        count: int = 25
    ) -> List[StreamComment]:
        """
        配信コメントブロックを生成
        
        Args:
            highlight_description: 本文のハイライトシーンの説明
            count: 生成するコメント数（デフォルト25件）
            
        Returns:
            StreamCommentオブジェクトのリスト
        """
        prompt = self._build_stream_prompt(highlight_description, count)
        
        try:
            raw_response = await self.llm.generate_text(purpose="social_reaction", prompt=prompt)
            comments_data = json.loads(str(raw_response).strip())
            
            comments = []
            for item in comments_data.get("comments", []):
                comments.append(StreamComment(
                    user=item.get("user", "匿名"),
                    text=item.get("text", ""),
                    timestamp=item.get("timestamp")
                ))
            
            logger.info(f"Generated {len(comments)} stream comments")
            return comments
            
        except Exception as e:
            logger.error(f"Failed to generate stream comments: {e}")
            # フォールバック: 簡易コメントを返す
            return self._generate_fallback_stream_comments(count)

    async def generate_forum_thread(
        self, 
        highlight_description: str, 
        post_count: int = 30
    ) -> List[ForumPost]:
        """
        掲示板スレッドを生成
        
        Args:
            highlight_description: 本文のハイライトシーンの説明
            post_count: 生成するレス数（デフォルト30件）
            
        Returns:
            ForumPostオブジェクトのリスト
        """
        prompt = self._build_forum_prompt(highlight_description, post_count)
        
        try:
            raw_response = await self.llm.generate_text(purpose="social_reaction", prompt=prompt)
            threads_data = json.loads(str(raw_response).strip())
            
            posts = []
            for i, item in enumerate(threads_data.get("posts", []), start=1):
                posts.append(ForumPost(
                    res_num=i,
                    name=item.get("name", "名無し"),
                    body=item.get("body", "")
                ))
            
            logger.info(f"Generated {len(posts)} forum posts")
            return posts
            
        except Exception as e:
            logger.error(f"Failed to generate forum thread: {e}")
            # フォールバック: 簡易スレッドを返す
            return self._generate_fallback_forum_posts(post_count)

    def _build_stream_prompt(self, highlight_description: str, count: int) -> str:
        """配信コメント生成用プロンプトを構築"""
        return f"""
以下のシーンに対する視聴者の配信コメントを{count}件生成してください。

シーン説明: {highlight_description}

## 出力形式
{{
  "comments": [
    {{
      "user": "ユーザー名",
      "text": "コメント内容",
      "timestamp": "ISO形式のタイムスタンプ（省略可）"
    }}
  ]
}}

## コメントの特徴
- ネットスラング（「ｗｗｗ」「！？」「草」「マジ？”等）を自然に使用
- 同接数の変化を言及（「同接50人突破！！」「同接100人越えwwww”等）
- ポジティブ・ネガティブ・困惑の反応をバランスよく含める
- 一件あたり10〜30文字程度
- 最後はまとめコメントで締める（「これはバズるわ”等）

## 禁止事項
- 差別的・攻撃的なコメント
- 過度な性的表現
- 50文字以上の長すぎるコメント
"""

    def _build_forum_prompt(self, highlight_description: str, post_count: int) -> str:
        """掲示板スレッド生成用プロンプトを構築"""
        return f"""
以下のシーンに対する5ch風掲示板スレッドを{post_count}レス生成してください。

シーン説明: {highlight_description}

## 出力形式
{{
  "posts": [
    {{
      "name": "ハンドルネーム",
      "body": "レス本文"
    }}
  ]
}}

## スレッドの特徴
- スレタイは「【悲報】」「【速報】」「【驚愕】」等で始まる
- 1行目は「イッチ」または「主」による状況説明
- 2ch/5ch特有の言い回し（「草」「マジ？」「これはひどい」「うpまだ？”等）
- 中盤以降は匿名IDでの論争や考察
- 末尾は「オワコン」「スレ立て乙」「次スレは○時頃”等の締めくくり
- 一件あたり20〜100文字程度
- 全体で50〜100レス程度

## 禁止事項
- 実在する人物・団体への中傷
- 過度な暴力描写やグロテスクな表現
- 法律違反を助長する内容
- スレタイが100文字以上
"""

    def _generate_fallback_stream_comments(self, count: int) -> List[StreamComment]:
        """LLM生成に失敗した場合のフォールバックコメント"""
        comments = []
        for i in range(count):
            comments.append(StreamComment(
                user=f"視聴者{i % 10 + 1}",
                text=f"わあああああああああああああああああああああああｗｗｗ",
            ))
        return comments

    def _generate_fallback_forum_posts(self, count: int) -> List[ForumPost]:
        """LLM生成に失敗した場合のフォールバックスレッド"""
        posts = []
        for i in range(count):
            posts.append(ForumPost(
                res_num=i+1,
                name=f"名無しさん{i+1:4d}",
                body=f"これはひどい... でもちょっと面白いかもｗｗｗ",
            ))
        return posts