import os
import time
from app.celery_worker import celery_app
from app.email_sender import send_qr_email


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def send_qr_email_task(self, to_email: str, student_name: str, 
                       event_name: str, qr_base64: str):
    """
    Celery task that sends a QR email asynchronously.
    Retries up to 3 times on failure.
    """
    try:
        success = send_qr_email(to_email, student_name, event_name, qr_base64)
        if not success:
            raise Exception("Email send returned False")
        return {"status": "success", "email": to_email}
    except Exception as exc:
        print(f"⚠️ Retrying email to {to_email} (attempt {self.request.retries + 1})")
        # Sleep briefly to avoid SMTP rate limits
        time.sleep(2)
        raise self.retry(exc=exc)