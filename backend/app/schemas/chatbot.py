from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

HISTORY_CONTENT_MAX = 2000


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=HISTORY_CONTENT_MAX)

    @field_validator("content", mode="before")
    @classmethod
    def clip_long_content(cls, value):
        # A long earlier answer is clipped, never rejected: a 422 here would break every later request.
        if isinstance(value, str) and len(value) > HISTORY_CONTENT_MAX:
            return value[: HISTORY_CONTENT_MAX - 1] + "…"
        return value


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, examples=["진주성 근처 냉면집 알려줘"])
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    today: date | None = Field(default=None, description="YYYY-MM-DD; honoured only in demo mode")

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("메시지를 입력해 주세요.")
        return value


class ChatSource(BaseModel):
    type: Literal["place", "post"]
    id: str
    label: str = Field(..., min_length=1, max_length=200)


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource] = Field(default_factory=list)
    # True when the answer is the deterministic search summary (no key, Claude failed, daily limit reached).
    fallback: bool = False
