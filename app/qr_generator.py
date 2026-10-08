import os
import io
import base64
import jwt
import qrcode
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

EVENT_SECRET = os.getenv("JWT_EVENT_SECRET", "default-secret-key")
JWT_ALGORITHM = "HS256"
QR_EXPIRY_HOURS = 48


def generate_qr_payload(student_email: str, student_roll_number: str, event_id: int) -> str:
    """
    Generate a cryptographically signed JWT for the attendee.
    This JWT will be encoded into the QR code.
    """
    payload = {
        "email": student_email,
        "roll": student_roll_number,
        "event_id": event_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=QR_EXPIRY_HOURS)
    }
    token = jwt.encode(payload, EVENT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def generate_qr_image_base64(jwt_token: str) -> str:
    """
    Convert JWT string into a QR code image and return it as base64.
    Useful for embedding in emails.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4
    )
    qr.add_data(jwt_token)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 for email embedding
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    return img_base64


def verify_qr_token(token: str) -> dict:
    """
    Verify a scanned QR token. Returns payload if valid, raises exception otherwise.
    """
    try:
        payload = jwt.decode(token, EVENT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("QR code has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid or forged QR code")