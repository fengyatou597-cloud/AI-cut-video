from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.demo_service import create_demo_project

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/seed")
def seed_demo_project(db: Session = Depends(get_db)):
    return create_demo_project(db)
