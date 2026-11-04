"""Insert demo Jinju reviews (idempotent by title). Usage: python -m app.scripts.seed_posts"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.board import BoardPost

DEMO_PASSWORD = "demo1234"

SEED_POSTS = [
    ("tour", "진주성 야경 산책 후기",
     "해 질 무렵 진주성에 올라 촉석루와 남강 풍경을 천천히 걸으며 봤어요. 성곽 조명이 켜지면 분위기가 확 달라져서 사진 찍기 좋았습니다."),
    ("tour", "국립진주박물관 임진왜란 전시 관람",
     "진주성 안에 있어서 산책 겸 들르기 좋았어요. 임진왜란 관련 전시가 차분하게 구성되어 있고 아이와 함께 보기에도 괜찮았습니다."),
    ("food", "하연옥 진주냉면 먹고 왔어요",
     "육전이 올라간 진주냉면을 먹었는데 국물이 담백하고 시원했어요. 점심 때는 대기가 있으니 조금 일찍 가는 걸 추천합니다."),
    ("food", "진주중앙시장 장보기와 길거리 간식",
     "중앙시장을 한 바퀴 돌며 제철 과일과 간식을 맛봤어요. 상인분들이 친절하고 가격도 합리적이라 구경하는 재미가 있었습니다."),
    ("festival", "남강유등축제 저녁 나들이",
     "남강 위에 떠 있는 유등이 정말 장관이었어요. 주말 저녁에는 사람이 많으니 평일 저녁이나 이른 시간대를 권해요."),
    ("festival", "진주논개제 행사 구경",
     "논개 제례와 공연을 가까이서 볼 수 있었어요. 진주성 일대에서 열려 산책과 함께 즐기기 좋았습니다."),
    ("free", "진주 당일치기 코스 공유",
     "오전에 진주성, 점심에 냉면, 오후에 중앙시장과 남강변 산책으로 하루를 보냈어요. 걸어서 이동할 수 있어 부담이 적었습니다."),
    ("free", "남강변 자전거 타기 좋아요",
     "남강 둔치를 따라 자전거 도로가 잘 이어져 있어요. 바람이 선선한 봄가을 오후에 타면 특히 기분 좋습니다."),
]


def seed(db: Session) -> int:
    """Insert missing posts; return how many were added."""
    added = 0
    for category, title, content in SEED_POSTS:
        if db.execute(select(BoardPost.id).where(BoardPost.title == title)).first():
            continue
        db.add(BoardPost(category=category, title=title, content=content, password=hash_password(DEMO_PASSWORD)))
        added += 1
    db.commit()
    return added


def main() -> None:
    from app.core.config import Settings
    from app.services.database import build_engine, build_session_factory

    engine = build_engine(Settings().database_url)
    try:
        with build_session_factory(engine)() as db:
            added = seed(db)
    finally:
        engine.dispose()
    print(f"seeded {added} new post(s)")


if __name__ == "__main__":
    main()
