from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.auth import require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/pending-volunteers", response_model=list[schemas.UserResponse])
def list_pending_volunteers(
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    return db.query(models.User).filter(models.User.is_approved == False).all()


@router.post("/approve-volunteer/{user_id}", response_model=schemas.UserResponse)
def approve_volunteer(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_approved = True
    db.commit()
    db.refresh(user)
    return user


@router.post("/create-event", response_model=schemas.EventResponse)
def create_event(
    event: schemas.EventCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    new_event = models.Event(
        event_name=event.event_name,
        event_date=event.event_date,
        secret_key=event.secret_key,
        created_by=admin.id
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event