from fastapi import APIRouter, Depends, HTTPException

from app.schemas.places import CollectionOut, MetaOut
from app.services.places_repo import PlacesRepo, get_places_repo

router = APIRouter()


@router.get("/meta", response_model=MetaOut)
def get_meta(repo: PlacesRepo = Depends(get_places_repo)):
    return repo.meta()


@router.get("/collection", response_model=CollectionOut)
def get_collection(repo: PlacesRepo = Depends(get_places_repo)):
    return repo.collection()


@router.get("/data/report")
def get_report(repo: PlacesRepo = Depends(get_places_repo)) -> dict:
    report = repo.report()
    if report is None:
        raise HTTPException(status_code=404, detail="report_not_found")
    return report
