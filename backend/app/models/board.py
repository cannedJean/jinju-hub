from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class BoardPost(Base):
    __tablename__ = "board_posts"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    # bcrypt hash (core.security). Never included in PostRead.
    password = Column(String(255), nullable=False)
    views = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # updated_at은 실제 글 수정 시에만 서비스에서 명시적으로 채운다 (조회수 증가로 갱신되면 안 됨).
    updated_at = Column(DateTime(timezone=True), nullable=True)
