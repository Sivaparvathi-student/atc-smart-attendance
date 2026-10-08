import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import base64
from dotenv import load_dotenv

load_dotenv()

MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "ALIET Techpreneur Club")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def send_qr_email(
    to_email: str,
    student_name: str,
    event_name: str,
    qr_base64: str
) -> bool:
    """
    Send the QR code to the attendee's email.
    Strict 1:1 mapping — this function only sends to `to_email`.
    """
    try:
        # Create message
        msg = MIMEMultipart("related")
        msg["Subject"] = f"🎟️ Your Entry Pass for {event_name}"
        msg["From"] = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"
        msg["To"] = to_email

        # HTML body
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
                <div style="max-width: 600px; margin: auto; background: #ffffff; 
                            padding: 30px; border-radius: 10px; 
                            border-top: 6px solid #FFC107;">
                    <h2 style="color: #000;">Hi {student_name}, 👋</h2>
                    <p style="color: #333; font-size: 15px;">
                        You are registered for <b>{event_name}</b>.
                        Here is your <b>secure entry pass</b>.
                    </p>
                    <div style="text-align: center; margin: 25px 0;">
                        <img src="cid:qrcode" 
                             alt="QR Code" 
                             style="width: 250px; height: 250px; 
                                    border: 3px solid #FFC107; 
                                    padding: 10px; border-radius: 10px;" />
                    </div>
                    <p style="color: #333; font-size: 14px;">
                        📌 Show this QR code at the entrance. 
                        Do <b>not</b> share it with anyone.
                    </p>
                    <p style="color: #888; font-size: 12px; margin-top: 30px;">
                        This QR is cryptographically signed and unique to you.
                        Sharing may result in rejection at the venue.
                    </p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #888; font-size: 12px; text-align: center;">
                        ALIET Techpreneur Club © 2026<br>
                        Innovate. Build. Lead.
                    </p>
                </div>
            </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html"))

        # Attach QR image inline
        img_bytes = base64.b64decode(qr_base64)
        img = MIMEImage(img_bytes, "png")
        img.add_header("Content-ID", "<qrcode>")
        img.add_header("Content-Disposition", "inline", filename="qrcode.png")
        msg.attach(img)

        # Send via SMTP
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)

        print(f"✅ Email sent to {to_email}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {str(e)}")
        return False