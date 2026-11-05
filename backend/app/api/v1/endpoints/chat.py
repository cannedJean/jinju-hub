from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.ratelimit import current_rate_limit, limiter
from app.schemas.chatbot import ChatRequest, ChatResponse
from app.services.chat_service import answer_chat
from app.services.database import get_db
from app.services.festival_status import effective_today
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
    settings = request.app.state.settings
    # Claude failures come back as the flagged fallback answer (200), never as an error.
    today = effective_today(body.today, settings.demo_date_override_enabled)
    return await answer_chat(body, repo, db, today, settings)
