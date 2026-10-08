# 🎟️ ATC Smart QR Attendance Pipeline

**ALIET Techpreneur Club** — Automated event check-in system with secure QR codes, email dispatch, and real-time Google Sheets sync.

## 🚀 Features

- ✅ Google Forms → PostgreSQL auto-sync
- ✅ Cryptographically signed JWT-based QR codes (anti-forgery)
- ✅ Asynchronous email delivery via Celery + Redis
- ✅ Mobile-friendly scanner (html5-qrcode)
- ✅ Anti-replay (duplicate scan detection)
- ✅ Real-time Google Sheets sync
- ✅ Live admin dashboard
- ✅ CSV export

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, FastAPI, SQLAlchemy |
| Database | PostgreSQL |
| Async Tasks | Celery + Redis |
| Email | Gmail SMTP |
| APIs | Google Sheets, Google Forms |
| Frontend | HTML5, JavaScript, html5-qrcode |

## 📦 Setup Instructions

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/atc-smart-attendance.git
cd atc-smart-attendance

# Create virtual environment
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Create .env file with:
#   DATABASE_URL, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
#   GOOGLE_SHEET_ID, GOOGLE_SERVICE_ACCOUNT_FILE, JWT_EVENT_SECRET
#   MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_FROM_NAME
#   REDIS_URL

# Add Google Service Account JSON
# Place service_account.json in project root

# Run the server
uvicorn app.main:app --reload

# In another terminal, run Celery worker
celery -A app.celery_worker.celery_app worker --loglevel=info --pool=solo