"""タスク入出力の Pydantic スキーマ。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class XPostResult(BaseModel):
    """X（旧Twitter）投稿案。"""

    primary: str = Field(description="本投稿（140字前後を目安）")
    alternatives: list[str] = Field(default_factory=list, description="別案")
    hashtags: list[str] = Field(default_factory=list)
    notes: str = Field(default="", description="運用メモ（投稿本文には含めない）")


class ToneIssue(BaseModel):
    severity: Literal["info", "warn", "block"]
    quote: str = Field(description="問題になりうる原文の抜粋")
    reason: str
    suggestion: str = Field(description="非助言寄りの言い換え案")


class ToneCheckResult(BaseModel):
    ok: bool = Field(description="block がなければ True")
    summary: str
    issues: list[ToneIssue] = Field(default_factory=list)


class SummaryResult(BaseModel):
    title: str
    bullets: list[str] = Field(min_length=1, max_length=8)
    one_liner: str = Field(description="1文の要約")
