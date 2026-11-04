from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.ratelimit import current_rate_limit, limiter
from app.schemas.chatbot import ChatRequest, ChatResponse
from app.services.chat_service import ChatUpstreamError, answer_chat
from app.services.database import get_db
from app.services.festival_status import kst_today
from app.services.places_repo import PlacesRepo, get_places_repo

router = APIRouter()


def _limit() -> str:
    # Evaluated per request so the app's configured value applies.
    return current_rate_limit()


@router.post("/chat", response_model=ChatResponse, summary="Ask the Jinju travel chatbot")
@limiter.limit(_limit)
async def chat(
    request: Request,
    body: ChatRequest,
    repo: PlacesRepo = Depends(get_places_repo),
    db: Session = Depends(get_db),
):
    try:
        return await answer_chat(body, repo, db, kst_today(), request.app.state.settings)
    except ChatUpstreamError:
        raise HTTPException(
            status_code=502, detail="챗봇 답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."
        ) from None
