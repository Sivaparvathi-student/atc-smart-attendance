from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.auth import require_admin
from app.google_forms import fetch_new_registrations
from app.qr_generator import generate_qr_payload, generate_qr_image_base64
from app.tasks import send_qr_email_task

router = APIRouter(prefix="/sync", tags=["Google Forms Sync"])


@router.post("/fetch-registrations")
def fetch_registrations(
    event_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """Fetch registrations from Google Forms and insert new attendees."""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    try:
        registrations = fetch_new_registrations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google Sheets error: {str(e)}")

    added = []
    skipped = []

    for reg in registrations:
        existing = db.query(models.Attendee).filter(
            models.Attendee.student_email == reg["student_email"],
            models.Attendee.event_id == event_id,
            models.Attendee.student_roll_number == reg["student_roll_number"]
        ).first()

        if existing:
            skipped.append(reg["student_email"])
            continue

        attendee = models.Attendee(
            student_email=reg["student_email"],
            event_id=event_id,
            student_roll_number=reg["student_roll_number"],
            student_name=reg["student_name"],
            status="Absent",
            qr_sent=False
        )
        db.add(attendee)
        added.append({
            "email": reg["student_email"],
            "roll": reg["student_roll_number"],
            "name": reg["student_name"]
        })

    db.commit()

    return {
        "event_id": event_id,
        "total_from_sheet": len(registrations),
        "added": len(added),
        "skipped_duplicates": len(skipped),
        "added_students": added
    }


@router.get("/preview-qr/{email}/{roll}/{event_id}")
def preview_qr(
    email: str,
    roll: str,
    event_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """Preview a QR code for a specific attendee."""
    attendee = db.query(models.Attendee).filter(
        models.Attendee.student_email == email,
        models.Attendee.event_id == event_id,
        models.Attendee.student_roll_number == roll
    ).first()

    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    jwt_token = generate_qr_payload(email, roll, event_id)
    qr_base64 = generate_qr_image_base64(jwt_token)

    return {
        "student_name": attendee.student_name,
        "student_email": attendee.student_email,
        "student_roll_number": attendee.student_roll_number,
        "jwt_token": jwt_token,
        "qr_image_base64": qr_base64,
        "note": "Copy the qr_image_base64 and paste in browser as: data:image/png;base64,<paste_here>"
    }


@router.post("/send-qr-emails/{event_id}")
def send_qr_emails_batch(
    event_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """Send QR codes to all attendees who haven't received them yet."""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    attendees = db.query(models.Attendee).filter(
        models.Attendee.event_id == event_id,
        models.Attendee.qr_sent == False
    ).all()

    if not attendees:
        return {"message": "No pending attendees to send emails", "queued": 0}

    queued = 0
    for attendee in attendees:
        jwt_token = generate_qr_payload(
            attendee.student_email,
            attendee.student_roll_number,
            event_id
        )
        qr_base64 = generate_qr_image_base64(jwt_token)

        send_qr_email_task.delay(
            attendee.student_email,
            attendee.student_name,
            event.event_name,
            qr_base64
        )

        attendee.qr_sent = True
        queued += 1

    db.commit()

    return {
        "event_id": event_id,
        "event_name": event.event_name,
        "queued": queued,
        "message": f"Queued {queued} emails — Celery worker is sending them."
    }


@router.post("/resend-qr/{email}/{roll}/{event_id}")
def resend_qr(
    email: str,
    roll: str,
    event_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """Resend QR to a specific attendee."""
    attendee = db.query(models.Attendee).filter(
        models.Attendee.student_email == email,
        models.Attendee.event_id == event_id,
        models.Attendee.student_roll_number == roll
    ).first()

    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    event = db.query(models.Event).filter(models.Event.id == event_id).first()

    jwt_token = generate_qr_payload(email, roll, event_id)
    qr_base64 = generate_qr_image_base64(jwt_token)

    send_qr_email_task.delay(email, attendee.student_name, event.event_name, qr_base64)

    return {"message": f"Resending QR to {email}"}