from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.database import engine, Base, SessionLocal
from app import models
from app.routes import auth_routes, admin_routes, sync_routes, scan_routes,dashboard_routes
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ALIET Techpreneur Club - Smart QR Attendance",
    description="Automated QR check-in engine with Google Sheets sync",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth_routes.router)
app.include_router(admin_routes.router)
app.include_router(sync_routes.router)
app.include_router(scan_routes.router)
app.include_router(dashboard_routes.router)

@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/health")
def health_check():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# Ensure static folder exists
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/scanner")
def scanner_ui():
    return FileResponse("static/scanner.html")
@app.get("/admin-dashboard")
def admin_dashboard_ui():
    return FileResponse("static/admin.html")
@app.get("/login")
def login_page():
    return FileResponse("static/login.html")

@app.get("/register")
def register_page():
    return FileResponse("static/register.html")

@app.get("/admin-panel")
def admin_panel_page():
    return FileResponse("static/admin-panel.html")