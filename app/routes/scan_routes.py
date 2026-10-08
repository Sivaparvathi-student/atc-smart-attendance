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
            # 🔽 Sync to Google Sheets (non-blocking — failures are logged)
    try:
        sync_scan_to_sheet(
            attendee.student_email,
            attendee.student_roll_number,
            event_id,
            attendee.check_in_time.strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        print(f"⚠️ Sheets sync failed (non-critical): {e}")
        return {
            "status": "INVALID",
            "message": f"❌ {str(e)}",
            "color": "red"
        }

    email = payload["email"]
    roll = payload["roll"]
    event_id = payload["event_id"]

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
    attendee.status = "Present"
    attendee.check_in_time = datetime.utcnow()

    db.add(models.ScanLog(
        attendee_email=email,
        attendee_event_id=event_id,
        attendee_roll_number=roll,
        scanned_by_volunteer_id=volunteer.id,
        scan_result="VALID"
    ))
    db.commit()

    return {
        "status": "VALID",
        "message": "✅ Welcome!",
        "color": "green",
        "student_name": attendee.student_name,
        "student_roll": attendee.student_roll_number,
        "student_email": attendee.student_email,
        "check_in_time": attendee.check_in_time.isoformat(),
        "scanned_by": volunteer.name
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