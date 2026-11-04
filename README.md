# JinjuHub — 진주시 공공 관광 웹사이트

진주시 공공데이터(진주시 OpenAPI · 한국관광공사 TourAPI)를 병렬 수집·정제·병합해 만든 장소 데이터 위에,
지도 중심 탐색과 "유등 밝히기" 게이미피케이션을 얹은 웹사이트입니다.

## 구조

```
JinjuHub/
├─ config/region.yaml   # 진주 지역 설정
├─ pipeline/            # 데이터 수집·정제 파이프라인 (Python)
├─ backend/             # FastAPI (places.db 읽기 전용 + 게시판 + 날씨 + Claude 챗봇)
├─ frontend/            # Vue 3 SPA (Leaflet 지도, 유등 게이미피케이션)
└─ docs/superpowers/    # 설계 명세와 구현 계획
```

자세한 내용: [설계 명세](docs/superpowers/specs/2026-11-04-jinjuhub-design.md) · [구현 계획](docs/superpowers/plans/2026-11-04-jinjuhub.md)
