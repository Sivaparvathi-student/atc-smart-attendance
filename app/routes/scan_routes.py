from app.sheets_sync import sync_scan_to_sheet
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.auth import get_current_user
from app.qr_generator import verify_qr_token

router = APIRouter(prefix="/scan", tags=["QR Scanner"])


@router.post("/verify")
def verify_qr(
    qr_data: dict,
    db: Session = Depends(get_db),
    volunteer: models.User = Depends(get_current_user)
):
    """
    Verify a scanned QR token and mark attendance.
    
    Request body: {"token": "<JWT string from QR>"}
    
    Returns:
      - VALID: attendance marked
      - ALREADY_CHECKED_IN: duplicate scan
      - INVALID: forgery detected
    """
    token = qr_data.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing token")

    # Step 1: Verify JWT signature
    try:
        payload = verify_qr_token(token)
    except ValueError as e:
        # Log the failed attempt
        db.add(models.ScanLog(
            attendee_email="UNKNOWN",
            attendee_event_id=0,
            attendee_roll_number="UNKNOWN",
            scanned_by_volunteer_id=volunteer.id,
            scan_result="INVALID"
        ))
        db.commit()
        return {
            "status": "INVALID",
            "message": f"❌ {str(e)}",
            "color": "red"
        }

    email = payload.get("email")
    roll = payload.get("roll")
    event_id = payload.get("event_id")

    if not email or not roll or not event_id:
        return {
            "status": "INVALID",
            "message": "❌ Invalid QR code payload",
            "color": "red"
        }

    # Step 2: Find attendee in DB (composite PK lookup)
    attendee = db.query(models.Attendee).filter(
        models.Attendee.student_email == email,
        models.Attendee.event_id == event_id,
        models.Attendee.student_roll_number == roll
    ).with_for_update().first()

    if not attendee:
        db.add(models.ScanLog(
            attendee_email=email,
            attendee_event_id=event_id,
            attendee_roll_number=roll,
            scanned_by_volunteer_id=volunteer.id,
            scan_result="NOT_REGISTERED"
        ))
        db.commit()
        return {
            "status": "INVALID",
            "message": "❌ Attendee not registered for this event",
            "color": "red"
        }

    # Step 3: Check for duplicate scan (race-condition-safe with row lock)
    if attendee.status == "Present":
        db.add(models.ScanLog(
            attendee_email=email,
            attendee_event_id=event_id,
            attendee_roll_number=roll,
            scanned_by_volunteer_id=volunteer.id,
            scan_result="ALREADY_CHECKED_IN"
        ))
        db.commit()
        return {
            "status": "ALREADY_CHECKED_IN",
            "message": f"⚠️ Already scanned at {attendee.check_in_time.strftime('%H:%M:%S')}",
            "color": "orange",
            "student_name": attendee.student_name,
            "student_roll": attendee.student_roll_number,
            "check_in_time": attendee.check_in_time.isoformat()
        }

    # Step 4: Mark attendance
    now = datetime.utcnow()
    attendee.status = "Present"
    attendee.check_in_time = now

    db.add(models.ScanLog(
        attendee_email=email,
        attendee_event_id=event_id,
        attendee_roll_number=roll,
        scanned_by_volunteer_id=volunteer.id,
        scan_result="VALID"
    ))
    db.commit()

    # Step 5: Sync to Google Sheets (non-blocking — attendance is already recorded)
    sheet_sync_status = "skipped"
    try:
        event = db.query(models.Event).filter(models.Event.id == event_id).first()
        sheet_id = event.sheet_id if event else None
        res = sync_scan_to_sheet(
            attendee.student_email,
            attendee.student_roll_number,
            event_id,
            now.strftime("%Y-%m-%d %H:%M:%S"),
            sheet_id=sheet_id
        )
        sheet_sync_status = res.get("status") if isinstance(res, dict) else "done"
    except Exception as e:
        print(f"[SCAN SHEET SYNC] Sheets sync failed (non-critical): {e}")
        sheet_sync_status = f"error: {str(e)}"

    return {
        "status": "VALID",
        "message": "✅ Welcome!",
        "color": "green",
        "student_name": attendee.student_name,
        "student_roll": attendee.student_roll_number,
        "student_email": attendee.student_email,
        "check_in_time": attendee.check_in_time.isoformat(),
        "scanned_by": volunteer.name,
        "sheet_sync": sheet_sync_status
    }


@router.get("/stats/{event_id}")
def event_stats(
    event_id: int,
    db: Session = Depends(get_db),
    volunteer: models.User = Depends(get_current_user)
):
    """Live stats for the scanner dashboard."""
    total = db.query(models.Attendee).filter(
        models.Attendee.event_id == event_id
    ).count()

    present = db.query(models.Attendee).filter(
        models.Attendee.event_id == event_id,
        models.Attendee.status == "Present"
    ).count()

    return {
        "event_id": event_id,
        "total_registered": total,
        "present": present,
        "absent": total - present
    }


@router.get("/active-events")
def list_active_events(
    db: Session = Depends(get_db),
    volunteer: models.User = Depends(get_current_user)
):
    """List all active events for volunteers to select on the scanner."""
    events = db.query(models.Event).filter(models.Event.is_active == True).order_by(models.Event.id.desc()).all()
    return [{
        "id": e.id,
        "event_name": e.event_name,
        "event_date": str(e.event_date)
    } for e in events]