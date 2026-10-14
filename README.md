# 🎟️ ATC Smart QR Attendance Pipeline

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-4169E1.svg?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-Queue-DC382D.svg?style=flat&logo=redis&logoColor=white)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-Async_Tasks-37814A.svg?style=flat&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An end-to-end automated event check-in and attendance management system designed for **ALIET Techpreneur Club (ATC)**. It eliminates manual sign-in sheets and ticket fraud by providing cryptographically signed QR passes, real-time Google Sheets synchronization, asynchronous email delivery, and a lightning-fast mobile camera scanner.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation & Setup](#-installation--setup)
- [Environment Configuration](#-environment-configuration)
- [Google Cloud Service Account Setup](#-google-cloud-service-account-setup)
- [Running the Application](#-running-the-application)
- [Frontend Portal Pages](#-frontend-portal-pages)
- [API Endpoints Reference](#-api-endpoints-reference)
- [Diagnostic & Testing Utilities](#-diagnostic--testing-utilities)
- [Security & Anti-Fraud Measures](#-security--anti-fraud-measures)
- [License & Acknowledgements](#-license--acknowledgements)

---

## 🌟 Overview

Managing college and club event attendance with paper sheets or simple forms is prone to proxy attendance, long queues, and data entry delays. 

**ATC Smart QR Attendance Pipeline** solves this by creating a closed-loop automated pipeline:
1. **Registration Sync:** Pulls attendee records directly from Google Forms response sheets into PostgreSQL.
2. **Secure Pass Generation:** Issues tamper-proof, time-bound, digitally signed QR codes for each verified attendee.
3. **Dispatch:** Dispatches personalized HTML entry passes via email (asynchronous queue via Celery + Redis).
4. **On-Site Verification:** Volunteers scan QR codes using any mobile or laptop browser with camera access.
5. **Real-Time Dual Update:** Records check-in timestamps in PostgreSQL and immediately updates Google Sheets live.
6. **Analytics & Export:** Admins observe real-time turnout metrics and export final data to CSV.

---

## ✨ Key Features

- **Google Forms & Sheets Integration:** Auto-detects columns (`Name`, `Email`, `Roll Number`) from Google Sheets responses and synchronizes registrations directly into the database.
- **Cryptographic Anti-Forgery QR Codes:** Encodes attendee payload into signed JWT tokens (`HS256`) with customizable expiration windows and event secrets.
- **Asynchronous Email Engine:** Sends responsive HTML entry tickets containing embedded inline QR passes (RFC-compliant multipart MIME with download fallback) via Celery + Redis or background workers.
- **Mobile-Friendly Web Scanner:** Built with `html5-qrcode` supporting real-time camera stream, front/rear camera toggle, audio-visual feedback, and manual roll number override.
- **Anti-Replay / Proxy Prevention:** Flags duplicate scan attempts instantly with exact previous check-in timestamps and preventing double entries.
- **Real-Time Live Sync:** Automatically writes back check-in status (`Present`) and UTC timestamps into linked Google Sheets.
- **Role-Based Access Control (RBAC):**
  - **Admins:** Event creation, volunteer approvals, sheet synchronization, email dispatch triggers, live statistics, and CSV data export.
  - **Volunteers:** Verified accounts with restricted access to event check-in scanner.
- **Live Admin Dashboard:** Visual metrics tracking total registrations, check-ins, remaining attendees, and volunteer activity logs.

---

## 🏛️ System Architecture

```text
  [ Google Form ]
         │
         ▼
  [ Google Sheets ] ──( gspread / Service Account )──┐
                                                     ▼
                                          [ FastAPI Backend Engine ]
                                          ├── Auth & Role Management
                                          ├── JWT Signing (HS256)
                                          └── Composite Key Anti-Replay
                                             │             │
                    ┌────────────────────────┘             └────────────────────────┐
                    ▼                                                               ▼
           [ PostgreSQL Database ]                                          [ Redis + Celery ]
           ├── Users (Admin/Volunteer)                                      └── Async Mail Tasks
           ├── Events                                                               │
           ├── Attendees (Email, Roll, EventID)                                     ▼
           └── Scan Logs (Audit Trail)                                      [ Attendee Inbox ]
                                                                            (HTML QR Entry Pass)
                    ▲
                    │ (Fast Check-in / Verification)
                    │
         [ Mobile Web Scanner ]
      (html5-qrcode / Camera Stream)
```

---

## 🛠️ Tech Stack

| Component | Technology | Description |
|---|---|---|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) | High-performance asynchronous REST API framework |
| **Server** | [Uvicorn](https://www.uvicorn.org/) | Lightning-fast ASGI web server |
| **Database** | [PostgreSQL](https://www.postgresql.org/) + [SQLAlchemy](https://www.sqlalchemy.org/) | Relational database with Object Relational Mapper |
| **Security & Auth** | [Passlib (bcrypt)](https://passlib.readthedocs.io/) + [PyJWT](https://pyjwt.readthedocs.io/) / [Python-Jose](https://github.com/mpdavis/python-jose) | Password hashing and signed JWT validation |
| **Task Queue** | [Celery](https://docs.celeryq.dev/) + [Redis](https://redis.io/) | Distributed task queue for non-blocking email delivery |
| **Google APIs** | [gspread](https://docs.gspread.org/) + [Google Drive / Sheets API](https://developers.google.com/sheets/api) | Sheet read/write automation with Service Accounts |
| **QR Generation** | [qrcode[pil]](https://pypi.org/project/qrcode/) | High-contrast RGB base64 QR generation |
| **Email Service** | [smtplib](https://docs.python.org/3/library/smtplib.html) (Gmail SMTP / TLS) | Responsive HTML email builder with MIME attachments |
| **Frontend** | HTML5, Vanilla CSS, JavaScript, [html5-qrcode](https://github.com/mebjas/html5-qrcode) | Responsive web portals and live camera scanner |

---

## 📁 Project Structure

```text
smart-attendance/
├── app/
│   ├── routes/
│   │   ├── admin_routes.py       # Event creation, volunteer approvals, user management
│   │   ├── auth_routes.py        # Login, registration, token issuance, current user
│   │   ├── dashboard_routes.py   # Overview metrics, scan logs, CSV exports
│   │   ├── scan_routes.py        # QR token verification, anti-replay, sheet updates
│   │   └── sync_routes.py        # Google Sheets fetch, QR preview, email dispatch
│   ├── auth.py                   # Password hashing, JWT token logic, route dependencies
│   ├── celery_worker.py          # Celery configuration & Redis broker bindings
│   ├── database.py               # SQLAlchemy database session & engine
│   ├── email_sender.py           # Multi-part RFC compliant HTML email builder
│   ├── google_forms.py           # Sheet authentication, column detection, parsing
│   ├── main.py                   # FastAPI initialization, CORS, static routes
│   ├── models.py                 # SQLAlchemy ORM schemas (Users, Events, Attendees, ScanLogs)
│   ├── qr_generator.py           # Cryptographic JWT payload encoder & QR image generator
│   ├── schemas.py                # Pydantic validation schemas
│   ├── sheets_sync.py            # Real-time scan result write-back to Google Sheets
│   └── tasks.py                  # Celery worker tasks with retry policies
├── static/
│   ├── admin-panel.html          # Extended administration console
│   ├── admin.html                # Event & attendee management dashboard
│   ├── index.html                # Main landing and navigation page
│   ├── login.html                # Authentication portal
│   ├── register.html             # Volunteer registration page
│   └── scanner.html              # Mobile-ready live QR scanner interface
├── .env                          # Environment variables configuration (ignored by git)
├── .gitignore                    # Git exclusions
├── create_tables.py              # Manual database tables initialisation script
├── diagnose.py                   # Google Service Account permission & connectivity tester
├── requirements.txt              # Python project dependencies
├── service_account.json          # Google Cloud Service Account credentials (keep private!)
├── test_db.py                    # Database connection health check script
└── test_sheet.py                 # Google Sheets read/write test script
```

---

## 📋 Prerequisites

Before setting up the project, ensure you have installed:
- **Python 3.10+**
- **PostgreSQL** (running locally or a cloud database such as Neon / Supabase / AWS RDS)
- **Redis** (running locally or cloud instance for Celery task queuing; optional if running in synchronous mode)
- **Google Cloud Console Account** (with Sheets API and Drive API enabled)
- **Gmail Account** (with an [App Password](https://myaccount.google.com/apppasswords) configured for SMTP)

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Sivaparvathi-student/atc-smart-attendance.git
cd atc-smart-attendance
```

### 2. Create and Activate Virtual Environment
**Windows (PowerShell / Command Prompt):**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Required Dependencies
```bash
pip install -r requirements.txt
```

*(Optional: If your environment needs the additional imaging and queuing packages, ensure they are installed):*
```bash
pip install celery redis qrcode[pil] gspread oauth2client pyjwt pydantic[email]
```

---

## ⚙️ Environment Configuration

Create a `.env` file in the root directory and populate it with your environment variables:

```ini
# ==========================================
# DATABASE SETTINGS (PostgreSQL)
# ==========================================
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/smart_attendance

# ==========================================
# JWT AUTHENTICATION
# ==========================================
SECRET_KEY=your_super_secret_jwt_key_here_change_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ==========================================
# EVENT QR SECURITY
# ==========================================
JWT_EVENT_SECRET=your_event_qr_signing_secret_key
QR_EXPIRY_HOURS=720

# ==========================================
# GOOGLE INTEGRATION
# ==========================================
GOOGLE_SHEET_ID=your_default_google_sheet_id_or_url
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

# ==========================================
# EMAIL DISPATCH (GMAIL SMTP)
# ==========================================
MAIL_USERNAME=your_club_email@gmail.com
MAIL_PASSWORD=your_16_character_app_password
MAIL_FROM=your_club_email@gmail.com
MAIL_FROM_NAME="ALIET Techpreneur Club"

# ==========================================
# TASK QUEUE (REDIS & CELERY)
# ==========================================
REDIS_URL=redis://localhost:6379/0
```

> [!TIP]
> For Gmail credentials, do **not** use your normal account password. Generate a 16-character **App Password** via:
> **Google Account Settings → Security → 2-Step Verification → App Passwords**.

---

## 🔑 Google Cloud Service Account Setup

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., `atc-smart-attendance`).
3. Enable both the **Google Sheets API** and **Google Drive API**.
4. Go to **IAM & Admin > Service Accounts** and click **Create Service Account**.
5. Grant the service account the **Editor** role.
6. Under the **Keys** tab, click **Add Key → Create new key (JSON)**.
7. Download the file, rename it to `service_account.json`, and place it in the root folder of this project.
8. Copy the `client_email` address from the JSON file (e.g., `attendance-bot@atc-attendance.iam.gserviceaccount.com`).
9. **Important:** Open your Google Form's linked Response Spreadsheet, click **Share**, and grant **Editor** access to that Service Account email!

---

## 💻 Running the Application

### 1. Initialize Database Tables
Run the database test and table creation script:
```bash
python test_db.py
python create_tables.py
```

### 2. Verify Google Sheets Connectivity
Verify that the service account can view and edit the sheet:
```bash
python diagnose.py
```

### 3. Start the FastAPI Server
```bash
uvicorn app.main:app --reload --port 8000
```
The application will be accessible at `http://localhost:8000`.
Interactive Swagger API documentation will be available at `http://localhost:8000/docs`.

### 4. Start Celery Worker (In a separate terminal)
To handle asynchronous email sending:

**Windows:**
```bash
celery -A app.celery_worker.celery_app worker --loglevel=info --pool=solo
```

**macOS / Linux:**
```bash
celery -A app.celery_worker.celery_app worker --loglevel=info
```

---

## 🖥️ Frontend Portal Pages

| Path | Purpose | Access |
|---|---|---|
| `/` | System Landing Page | Public |
| `/login` | User Authentication | Public |
| `/register` | Volunteer Registration | Public (Pending Admin Approval) |
| `/scanner` | Mobile-Optimized QR Camera Scanner | Authenticated Volunteers & Admins |
| `/admin-dashboard` | Attendance Management, Sync, Email Dispatch | Approved Admins Only |
| `/admin-panel` | User Role Approvals and Event Management | Approved Admins Only |

---

## 📡 API Endpoints Reference

### 🔐 Authentication (`/auth`)
- `POST /auth/register` — Register a new volunteer account.
- `POST /auth/login` — Authenticate and receive JWT bearer token.
- `GET /auth/me` — Retrieve profile information of current logged-in user.

### 🛡️ Administration (`/admin`)
- `GET /admin/pending-volunteers` — List users awaiting approval.
- `POST /admin/approve-volunteer/{user_id}` — Approve volunteer account.
- `POST /admin/promote-to-admin/{user_id}` — Elevate user to admin role.
- `DELETE /admin/reject-volunteer/{user_id}` — Reject and remove user.
- `POST /admin/create-event` — Create a new event and configure Sheet ID.
- `GET /admin/all-events` — List all registered events.
- `PATCH /admin/events/{event_id}` — Update event details or active status.

### 🔄 Sheets Synchronization & Email (`/sync`)
- `GET /sync/service-account-email` — View bot email to share sheets with.
- `GET /sync/test-sheet-access/{event_id}` — Test read access to event sheet.
- `POST /sync/fetch-registrations` — Ingest registrations from Google Sheets.
- `GET /sync/preview-qr/{email}/{roll}/{event_id}` — Inspect raw QR data and preview base64 ticket.
- `POST /sync/send-qr-emails/{event_id}` — Dispatch QR passes via background tasks / Celery.
- `POST /sync/resend-qr/{email}/{roll}/{event_id}` — Re-send pass to a specific attendee.

### 📷 Scanner & Attendance (`/scan`)
- `POST /scan/verify` — Decode token, check validity, anti-replay verification, and sync status.
- `GET /scan/active-events` — Fetch active events for volunteer selection.
- `GET /scan/stats/{event_id}` — Live count of Present vs Absent attendees.

### 📊 Dashboard & Reporting (`/dashboard`)
- `GET /dashboard/overview/{event_id}` — Summary statistics for an event.
- `GET /dashboard/scan-logs/{event_id}` — Chronological log of all scan attempts.
- `GET /dashboard/attendees/{event_id}` — Filterable list of all attendees and check-in statuses.
- `GET /dashboard/export-csv/{event_id}` — Download formatted attendance spreadsheet as CSV.

---

## 🧪 Diagnostic & Testing Utilities

The project includes purpose-built scripts to diagnose environmental issues:

```bash
# 1. Test database connectivity
python test_db.py

# 2. Test Google Service Account credentials & sheet visibility
python diagnose.py

# 3. Test sheet reading & writing
python test_sheet.py
```

---

## 🔒 Security & Anti-Fraud Measures

1. **Anti-Replay Mechanism:** Each check-in uses a composite key of `(student_email, event_id, student_roll_number)`. Once scanned, status flips to `Present` with an immutable timestamp. Re-scanning immediately triggers a `DUPLICATE_SCAN` alert displaying the original check-in time.
2. **Cryptographic Token Integrity:** QR contents contain signed JSON Web Tokens (`HS256`). Any student altering roll numbers or event IDs invalidates the signature, triggering an `INVALID_TOKEN` alert.
3. **Account Approval Gates:** Newly registered volunteers cannot log in or scan until explicitly verified and activated by an Admin.
4. **Credential Isolation:** Service accounts and SMTP credentials operate through isolated environment variables and service JSON keys strictly excluded from version control.

---

## 👥 Authors & Acknowledgements

Developed with ❤️ for **ALIET Techpreneur Club (ATC)**.
- **Institution:** Andhra Loyola Institute of Engineering and Technology (ALIET)
- **Club:** ALIET Techpreneur Club

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
