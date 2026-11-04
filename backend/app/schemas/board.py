from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# 프론트 POST_CATEGORIES와 동일한 값이 source of truth
ALLOWED_CATEGORIES = ("tour", "food", "festival", "free")


class PostBase(BaseModel):
    category: Literal["tour", "food", "festival", "free"] = Field(
        ..., examples=["tour"]
    )
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=5000)


class PostCreate(PostBase):
    password: str = Field(..., min_length=4, max_length=20)


class PostUpdate(PostBase):
    # 수정 시에도 비밀번호로 본인 확인 (서버에서 저장값과 대조, 불일치 시 403)
    password: str = Field(..., min_length=4, max_length=20)


class PostDelete(BaseModel):
    password: str = Field(..., min_length=4, max_length=20)


class PostRead(PostBase):
    id: int
    views: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PostListResponse(BaseModel):
    items: list[PostRead]
    total: int
    page: int
    size: int
    totalPages: int
