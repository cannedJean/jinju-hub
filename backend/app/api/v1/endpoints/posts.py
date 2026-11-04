from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.ratelimit import current_rate_limit, limiter
from app.core.security import verify_password
from app.schemas.board import PostCreate, PostDelete, PostListResponse, PostRead, PostUpdate
from app.services import board_service
from app.services.database import get_db

router = APIRouter()


def _limit() -> str:
    # Evaluated per request so the app's configured value applies.
    return current_rate_limit()


@router.get("", response_model=PostListResponse, summary="List posts (paginated)")
def list_posts(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    keyword: str | None = Query(None),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
):
    items, total = board_service.get_posts(db, page, size, keyword, category)
    total_pages = (total + size - 1) // size if total else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "totalPages": total_pages,
    }


@router.post("", response_model=PostRead, status_code=201, summary="Create a post")
@limiter.limit(_limit)
def create_post(request: Request, post: PostCreate, db: Session = Depends(get_db)):
    return board_service.create_post(db, post)


@router.get("/{post_id}", response_model=PostRead, summary="Get a post (increments views unless count_view=false)")
def get_post(post_id: int, count_view: bool = Query(True), db: Session = Depends(get_db)):
    post = board_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="존재하지 않는 게시글입니다.")
    return board_service.increment_views(db, post) if count_view else post


@router.put("/{post_id}", response_model=PostRead, summary="Update a post (password verified)")
@limiter.limit(_limit)
def update_post(request: Request, post_id: int, payload: PostUpdate, db: Session = Depends(get_db)):
    post = board_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="존재하지 않는 게시글입니다.")
    if not verify_password(payload.password, post.password):
        raise HTTPException(status_code=403, detail="비밀번호가 일치하지 않습니다.")
    return board_service.update_post(db, post, payload)


@router.delete("/{post_id}", status_code=204, summary="Delete a post (password verified)")
@limiter.limit(_limit)
def delete_post(request: Request, post_id: int, payload: PostDelete, db: Session = Depends(get_db)):
    post = board_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="존재하지 않는 게시글입니다.")
    if not verify_password(payload.password, post.password):
        raise HTTPException(status_code=403, detail="비밀번호가 일치하지 않습니다.")
    board_service.delete_post(db, post)
    return Response(status_code=204)
