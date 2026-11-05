from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.board import BoardPost
from app.schemas.board import PostCreate, PostUpdate


def _like_pattern(term: str) -> str:
    """Contains-pattern with LIKE wildcards (% _) and the escape char itself neutralised."""
    escaped = term.replace("\\", "\\\\").replace("%", "\%").replace("_", "\_")
    return f"%{escaped}%"


def get_posts(db: Session, page: int, size: int, keyword: str | None = None, category: str | None = None):
    query = db.query(BoardPost)

    if category:
        query = query.filter(BoardPost.category == category)

    if keyword:
        like = _like_pattern(keyword)
        query = query.filter(
            or_(BoardPost.title.ilike(like, escape="\\"), BoardPost.content.ilike(like, escape="\\"))
        )

    total = query.count()
    items = (
        query.order_by(BoardPost.created_at.desc(), BoardPost.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return items, total


def search_posts(db: Session, terms: list[str], category: str | None = None, limit: int = 5):
    """Search chatbot sources with OR semantics for short natural-language terms."""
    query = db.query(BoardPost)

    if category:
        query = query.filter(BoardPost.category == category)

    cleaned_terms = [term.strip() for term in terms if term.strip()]
    if cleaned_terms:
        predicates = []
        for term in cleaned_terms:
            like = _like_pattern(term)
            predicates.extend((BoardPost.title.ilike(like, escape="\\"), BoardPost.content.ilike(like, escape="\\")))
        query = query.filter(or_(*predicates))

    return query.order_by(BoardPost.created_at.desc(), BoardPost.id.desc()).limit(limit).all()


def get_post(db: Session, post_id: int):
    return db.query(BoardPost).filter(BoardPost.id == post_id).first()


def increment_views(db: Session, post: BoardPost):
    post.views = (post.views or 0) + 1
    db.commit()
    db.refresh(post)
    return post


def create_post(db: Session, post_data: PostCreate):
    data = post_data.model_dump()
    data["password"] = hash_password(data["password"])
    post = BoardPost(**data)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def update_post(db: Session, post: BoardPost, post_data: PostUpdate):
    # 비밀번호는 변경하지 않고 본문/카테고리만 갱신
    post.category = post_data.category
    post.title = post_data.title
    post.content = post_data.content
    post.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, post: BoardPost):
    db.delete(post)
    db.commit()
