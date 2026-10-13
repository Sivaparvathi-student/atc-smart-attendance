import os
import base64
import traceback
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.auth import require_admin
from app.google_forms import (
    fetch_new_registrations,
    get_service_account_email,
    get_sheet_client,
    clean_sheet_id,
    get_drive_file_info
)
from app.qr_generator import generate_qr_payload, generate_qr_image_base64
from app.email_sender import send_qr_email

router = APIRouter(prefix="/sync", tags=["Google Forms Sync"])


def _safe_print(text: str):
    """Print safely without crashing on Windows console encodings (cp1252)."""
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        try:
            print(text.encode("ascii", "replace").decode("ascii"), flush=True)
        except Exception:
            pass


@router.get("/service-account-email")
def service_account_email():
    """Get the Google Service Account email that sheets must be shared with."""
    return {"client_email": get_service_account_email()}


@router.get("/test-sheet-access/{event_id}")
def test_sheet_access(
    event_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """Test if Google Sheets API can open the sheet for an event."""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    raw_sheet_id = event.sheet_id or os.getenv("GOOGLE_SHEET_ID")
    if not raw_sheet_id:
        return {
            "status": "error",
            "message": "No Google Sheet ID configured for this event.",
            "bot_email": get_service_account_email()
        }

    sheet_id = clean_sheet_id(raw_sheet_id)

    try:
        client = get_sheet_client()
        sheet = client.open_by_key(sheet_id)
        ws = sheet.get_worksheet(0)
        rows = ws.get_all_values()
        return {
            "status": "success",
            "title": sheet.title,
            "sheet_id": sheet_id,
            "total_rows": len(rows),
            "headers": rows[0] if rows else [],
            "bot_email": get_service_account_email()
        }
    except Exception as e:
        bot_email = get_service_account_email()
        drive_info = get_drive_file_info(sheet_id)
        if drive_info and drive_info.get("mimeType") == "application/vnd.google-apps.form":
            form_name = drive_info.get("name", "Google Form")
            return {
                "status": "is_form",
                "sheet_id": sheet_id,
                "title": form_name,
                "message": f"This ID is a Google Form ('{form_name}'), NOT a Google Sheet!",
                "instructions": (
                    f"To connect responses:\n"
                    f"1. Open your Google Form ('{form_name}').\n"
                    f"2. Click the 'Responses' tab at the top.\n"
                    f"3. Click the green 'Link to Sheets' (or 'View in Sheets') icon to open the spreadsheet.\n"
                    f"4. In that Google Sheet, click the 'Share' button (top right) and add:\n"
                    f"   {bot_email} as Editor.\n"
                    f"5. Copy that spreadsheet's URL or ID and paste it here."
                ),
                "bot_email": bot_email
            }
        return {
            "status": "error",
            "sheet_id": sheet_id,
            "message": str(e),
            "hint": f"Ensure the Google Sheet (Responses spreadsheet) is shared with '{bot_email}' as Editor.",
            "bot_email": bot_email
        }


@router.post("/fetch-registrations")
def fetch_registrations(
    event_id: int,
    background_tasks: BackgroundTasks,
    auto_send_qr: bool = True,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """
    Fetch registrations from Google Forms/Sheets, insert new attendees,
    and automatically dispatch their QR pass emails in the background.
    """
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    raw_sheet_id = event.sheet_id or os.getenv("GOOGLE_SHEET_ID")
    if not raw_sheet_id:
        bot_email = get_service_account_email()
        raise HTTPException(
            status_code=400,
            detail=f"This event has no Google Sheet ID configured. Please edit the event and add the Google Sheet ID. (Remember to share the sheet with {bot_email})"
        )

    sheet_id = clean_sheet_id(raw_sheet_id)

    _safe_print(f"\n{'='*60}")
    _safe_print(f"[SYNC] Starting sheet sync for Event ID: {event_id} ({event.event_name})")
    _safe_print(f"       Sheet ID: {sheet_id}")
    _safe_print(f"{'='*60}\n")

    try:
        registrations = fetch_new_registrations(sheet_id)
        _safe_print(f"[SYNC] Fetched {len(registrations)} rows from Sheet")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        _safe_print(f"[SYNC ERROR] Failed to fetch registrations: {str(e)}")
        bot_email = get_service_account_email()
        raise HTTPException(
            status_code=500,
            detail=f"Google Sheets error: {str(e)}. Make sure the sheet is shared with Editor permission to {bot_email}"
        )

    added = []
    skipped = []
    new_attendees = []

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
        new_attendees.append(attendee)
        added.append({
            "email": reg["student_email"],
            "roll": reg["student_roll_number"],
            "name": reg["student_name"]
        })

    # Commit new attendees to DB first
    db.commit()

    # Automatically generate and queue QR emails for all newly synced attendees
    emails_queued = 0
    if auto_send_qr and new_attendees:
        for att in new_attendees:
            jwt_token = generate_qr_payload(
                att.student_email,
                att.student_roll_number,
                event_id
            )
            qr_b64 = generate_qr_image_base64(jwt_token)

            background_tasks.add_task(
                send_qr_email,
                att.student_email,
                att.student_name,
                event.event_name,
                qr_b64
            )
            att.qr_sent = True
            emails_queued += 1

        db.commit()

    _safe_print(f"[SYNC COMPLETE] Added: {len(added)}, Skipped: {len(skipped)}, QR Emails Queued: {emails_queued}\n")

    return {
        "event_id": event_id,
        "total_from_sheet": len(registrations),
        "added": len(added),
        "skipped_duplicates": len(skipped),
        "added_students": added,
        "emails_queued": emails_queued,
        "message": (
            f"Successfully synced {len(added)} attendee(s)."
            + (f" Queued {emails_queued} QR pass email(s) for delivery." if emails_queued > 0 else "")
        )
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
        "image_data_url": f"data:image/png;base64,{qr_base64}"
    }


@router.get("/qr-image/{email}/{roll}/{event_id}")
def qr_image(
    email: str,
    roll: str,
    event_id: int,
    db: Session = Depends(get_db)
):
    """Direct PNG image endpoint to display/preview an attendee's QR code in an <img> tag."""
    attendee = db.query(models.Attendee).filter(
        models.Attendee.student_email == email,
        models.Attendee.event_id == event_id,
        models.Attendee.student_roll_number == roll
    ).first()

    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    jwt_token = generate_qr_payload(email, roll, event_id)
    qr_base64 = generate_qr_image_base64(jwt_token)
    img_bytes = base64.b64decode(qr_base64)
    return Response(content=img_bytes, media_type="image/png")


@router.post("/send-qr-emails/{event_id}")
def send_qr_emails_batch(
    event_id: int,
    background_tasks: BackgroundTasks,
    force_all: bool = False,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """Send QR codes to all attendees who haven't received them yet (or all if force_all=True)."""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    query = db.query(models.Attendee).filter(models.Attendee.event_id == event_id)
    if not force_all:
        query = query.filter(models.Attendee.qr_sent == False)

    attendees = query.all()
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

        background_tasks.add_task(
            send_qr_email,
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
        "message": f"Successfully queued {queued} email(s) for delivery."
    }


@router.post("/resend-qr/{email}/{roll}/{event_id}")
def resend_qr(
    email: str,
    roll: str,
    event_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """Resend QR pass directly to a specific attendee."""
    attendee = db.query(models.Attendee).filter(
        models.Attendee.student_email == email,
        models.Attendee.event_id == event_id,
        models.Attendee.student_roll_number == roll
    ).first()

    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    jwt_token = generate_qr_payload(email, roll, event_id)
    qr_base64 = generate_qr_image_base64(jwt_token)

    background_tasks.add_task(
        send_qr_email,
        email,
        attendee.student_name,
        event.event_name,
        qr_base64
    )

    attendee.qr_sent = True
    db.commit()

    return {"message": f"QR entry pass queued for delivery to {email}"}