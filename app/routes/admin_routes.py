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


@router.get("/all-users", response_model=list[schemas.UserResponse])
def list_all_users(
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    return db.query(models.User).order_by(models.User.id).all()


@router.get("/all-events", response_model=list[schemas.EventResponse])
def list_all_events(
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    return db.query(models.Event).order_by(models.Event.id.desc()).all()


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


@router.post("/promote-to-admin/{user_id}", response_model=schemas.UserResponse)
def promote_to_admin(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = "admin"
    user.is_approved = True
    db.commit()
    db.refresh(user)
    return user


@router.delete("/reject-volunteer/{user_id}")
def reject_volunteer(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """Reject a pending volunteer registration (deletes from DB)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Cannot reject an admin account")

    email = user.email
    db.delete(user)
    db.commit()
    return {"message": f"User {email} rejected and removed."}


@router.delete("/delete-user/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """Permanently delete a user (volunteer only)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Cannot delete an admin account")
    if user.id == admin.id:
        raise HTTPException(status_code=403, detail="Cannot delete your own account")

    email = user.email
    db.delete(user)
    db.commit()
    return {"message": f"User {email} permanently deleted."}


from app.google_forms import clean_sheet_id


@router.post("/create-event", response_model=schemas.EventResponse)
def create_event(
    event: schemas.EventCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    clean_id = clean_sheet_id(event.sheet_id) if event.sheet_id else None
    new_event = models.Event(
        event_name=event.event_name,
        event_date=event.event_date,
        secret_key=event.secret_key,
        sheet_id=clean_id,
        created_by=admin.id
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event


@router.put("/events/{event_id}", response_model=schemas.EventResponse)
@router.patch("/events/{event_id}", response_model=schemas.EventResponse)
def update_event(
    event_id: int,
    event_data: schemas.EventUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """Update event properties, such as Google Sheet ID, event name, or active status."""
    ev = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    if event_data.event_name is not None:
        ev.event_name = event_data.event_name
    if event_data.event_date is not None:
        ev.event_date = event_data.event_date
    if event_data.secret_key is not None:
        ev.secret_key = event_data.secret_key
    if event_data.sheet_id is not None:
        ev.sheet_id = clean_sheet_id(event_data.sheet_id) if event_data.sheet_id else None
    if event_data.is_active is not None:
        ev.is_active = event_data.is_active

    db.commit()
    db.refresh(ev)
    return ev