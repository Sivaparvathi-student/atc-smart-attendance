from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app import models
from app.auth import require_admin

router = APIRouter(prefix="/dashboard", tags=["Admin Dashboard"])


@router.get("/overview/{event_id}")
def overview(
    event_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """Live overview for the admin dashboard."""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    total = db.query(models.Attendee).filter(
        models.Attendee.event_id == event_id
    ).count()

    present = db.query(models.Attendee).filter(
        models.Attendee.event_id == event_id,
        models.Attendee.status == "Present"
    ).count()

    return {
        "event_id": event_id,
        "event_name": event.event_name,
        "event_date": str(event.event_date),
        "total_registered": total,
        "present": present,
        "absent": total - present,
        "attendance_percentage": round((present / total * 100), 2) if total > 0 else 0
    }


@router.get("/scan-logs/{event_id}")
def scan_logs(
    event_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """Recent scan activity."""
    logs = db.query(models.ScanLog).filter(
        models.ScanLog.attendee_event_id == event_id
    ).order_by(models.ScanLog.scan_time.desc()).limit(limit).all()

    result = []
    for log in logs:
        volunteer = db.query(models.User).filter(
            models.User.id == log.scanned_by_volunteer_id
        ).first()
        result.append({
            "id": log.id,
            "attendee_email": log.attendee_email,
            "attendee_roll": log.attendee_roll_number,
            "volunteer_name": volunteer.name if volunteer else "Unknown",
            "scan_time": log.scan_time.isoformat(),
            "scan_result": log.scan_result
        })
    return result


@router.get("/volunteer-activity/{event_id}")
def volunteer_activity(
    event_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """See how many scans each volunteer has done."""
    volunteers = db.query(models.User).filter(
        models.User.role.in_(["admin", "volunteer"])
    ).all()

    result = []
    for v in volunteers:
        total_scans = db.query(models.ScanLog).filter(
            models.ScanLog.scanned_by_volunteer_id == v.id,
            models.ScanLog.attendee_event_id == event_id
        ).count()

        valid_scans = db.query(models.ScanLog).filter(
            models.ScanLog.scanned_by_volunteer_id == v.id,
            models.ScanLog.attendee_event_id == event_id,
            models.ScanLog.scan_result == "VALID"
        ).count()

        if total_scans > 0:
            result.append({
                "volunteer_id": v.id,
                "volunteer_name": v.name,
                "email": v.email,
                "total_scans": total_scans,
                "valid_scans": valid_scans,
                "invalid_scans": total_scans - valid_scans
            })

    return sorted(result, key=lambda x: x["valid_scans"], reverse=True)


@router.get("/export-csv/{event_id}")
def export_csv(
    event_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """Export attendance as CSV-friendly list."""
    attendees = db.query(models.Attendee).filter(
        models.Attendee.event_id == event_id
    ).all()

    csv_rows = [["Email", "Roll Number", "Name", "Status", "Check-In Time"]]
    for a in attendees:
        csv_rows.append([
            a.student_email,
            a.student_roll_number,
            a.student_name,
            a.status,
            a.check_in_time.isoformat() if a.check_in_time else ""
        ])

    return {"event_id": event_id, "rows": csv_rows, "count": len(csv_rows) - 1}
@router.get("/attendees/{event_id}")
def list_attendees(
    event_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """List all attendees for an event."""
    attendees = db.query(models.Attendee).filter(
        models.Attendee.event_id == event_id
    ).order_by(models.Attendee.student_email).all()

    return [{
        "student_email": a.student_email,
        "student_roll_number": a.student_roll_number,
        "student_name": a.student_name,
        "status": a.status,
        "check_in_time": a.check_in_time.isoformat() if a.check_in_time else None,
        "qr_sent": a.qr_sent
    } for a in attendees]


@router.get("/global-stats")
def global_stats(
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """Aggregate statistics for admin panel overview."""
    total_events = db.query(models.Event).count()
    total_users = db.query(models.User).count()
    pending_users = db.query(models.User).filter(models.User.is_approved == False).count()
    total_attendees = db.query(models.Attendee).count()
    total_present = db.query(models.Attendee).filter(models.Attendee.status == "Present").count()

    return {
        "total_events": total_events,
        "total_users": total_users,
        "pending_users": pending_users,
        "total_attendees": total_attendees,
        "total_present": total_present
    }