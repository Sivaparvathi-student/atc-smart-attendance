import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import base64
import sys
from dotenv import load_dotenv

load_dotenv()

MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "ALIET Techpreneur Club")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def _safe_print(text: str):
    """Print safely without crashing on Windows console code pages (cp1252)."""
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        try:
            print(text.encode("ascii", "replace").decode("ascii"), flush=True)
        except Exception:
            pass


def send_qr_email(
    to_email: str,
    student_name: str,
    event_name: str,
    qr_base64: str
) -> bool:
    """
    Send the QR entry pass to attendee's email.
    Uses RFC-compliant multipart/mixed + multipart/related + multipart/alternative
    structure for 100% compatibility across Gmail (Web & Mobile), Outlook, and Apple Mail,
    including both an inline image and a downloadable attachment fallback.
    """
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        _safe_print(f"[EMAIL ERROR] Missing MAIL_USERNAME or MAIL_PASSWORD in .env")
        return False

    try:
        # Strip data URL prefix if present (e.g., 'data:image/png;base64,...')
        if "," in qr_base64:
            qr_base64 = qr_base64.split(",", 1)[1].strip()

        img_bytes = base64.b64decode(qr_base64)

        # 1. Root container: multipart/mixed (holds related body + file attachments)
        msg_root = MIMEMultipart("mixed")
        msg_root["Subject"] = f"Your Entry Pass for {event_name}"
        msg_root["From"] = f"{MAIL_FROM_NAME} <{MAIL_FROM or MAIL_USERNAME}>"
        msg_root["To"] = to_email

        # 2. Related container: holds the HTML body + its inline images
        msg_related = MIMEMultipart("related")
        msg_root.attach(msg_related)

        # 3. Alternative container: holds plain text + rich HTML alternatives
        msg_alt = MIMEMultipart("alternative")
        msg_related.attach(msg_alt)

        # Plain text fallback
        plain_body = (
            f"Hi {student_name},\n\n"
            f"You are registered for {event_name}.\n"
            f"Your secure entry pass QR code is attached to this email as 'entry_pass_qr.png'.\n"
            f"Please show this QR code at the entrance.\n\n"
            f"ALIET Techpreneur Club\n"
        )
        msg_alt.attach(MIMEText(plain_body, "plain", "utf-8"))

        # Rich HTML body referencing inline cid:qrcode
        html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, -apple-system, sans-serif; background-color: #f4f4f5; margin: 0; padding: 20px;">
    <div style="max-width: 580px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-top: 6px solid #FFC107;">
        <div style="padding: 28px 24px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <span style="display: inline-block; background: #FFC107; color: #000; font-weight: bold; font-size: 11px; padding: 4px 12px; border-radius: 20px; text-transform: uppercase; letter-spacing: 1px;">Official Entry Pass</span>
            </div>
            <h2 style="color: #111; margin-top: 0; font-size: 22px; text-align: center;">Hi {student_name}, 👋</h2>
            <p style="color: #444; font-size: 15px; line-height: 1.5; text-align: center; margin: 8px 0 20px 0;">
                You are registered for <strong style="color: #000;">{event_name}</strong>.<br>
                Here is your <strong>secure QR entry pass</strong>:
            </p>

            <div style="text-align: center; margin: 25px auto; background: #fdfdfd; padding: 20px; border-radius: 12px; border: 2px dashed #FFC107; max-width: 300px;">
                <img src="cid:qrcode" 
                     alt="QR Code Entry Pass" 
                     width="240" 
                     height="240" 
                     style="display: block; margin: 0 auto; border-radius: 8px; max-width: 100%; height: auto;" />
                <p style="color: #777; font-size: 11px; margin: 10px 0 0 0;">
                    (Can't see the image? Use the attached <b>entry_pass_qr.png</b>)
                </p>
            </div>

            <div style="background-color: #fffbeb; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 6px; margin: 20px 0;">
                <p style="color: #92400e; font-size: 13px; margin: 0; font-weight: 500;">
                    📌 Show this QR code on your phone at the entrance. Do not share it with anyone.
                </p>
            </div>

            <p style="color: #888; font-size: 12px; line-height: 1.4; text-align: center; margin-top: 25px;">
                🔒 This QR pass is cryptographically signed and unique to your registration.<br>
                Sharing will result in immediate rejection at the scanner gate.
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
            <p style="color: #999; font-size: 12px; text-align: center; margin: 0;">
                ALIET Techpreneur Club © 2026<br>
                <em>Innovate. Build. Lead.</em>
            </p>
        </div>
    </div>
</body>
</html>
"""
        msg_alt.attach(MIMEText(html_body, "html", "utf-8"))

        # 4. Attach inline QR image (matching <img src="cid:qrcode">)
        inline_img = MIMEImage(img_bytes, "png")
        inline_img.add_header("Content-ID", "<qrcode>")
        inline_img.add_header("Content-Disposition", "inline")
        msg_related.attach(inline_img)

        # 5. ALSO attach explicit downloadable file (entry_pass_qr.png)
        # Guarantees that clients with blocked inline images can still open/save the pass!
        attach_img = MIMEImage(img_bytes, "png")
        attach_img.add_header("Content-Disposition", "attachment", filename="entry_pass_qr.png")
        msg_root.attach(attach_img)

        # Send via SMTP
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg_root)

        _safe_print(f"[EMAIL SUCCESS] QR Entry Pass sent to {to_email}")
        return True

    except Exception as e:
        _safe_print(f"[EMAIL ERROR] Failed to send email to {to_email}: {str(e)}")
        return False