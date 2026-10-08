from datetime import datetime, date
from sqlalchemy import String, Integer, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="volunteer")
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_name: Mapped[str] = mapped_column(String(150), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    secret_key: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))


class Attendee(Base):
    __tablename__ = "attendees"

    # COMPOSITE PRIMARY KEY
    student_email: Mapped[str] = mapped_column(String(100), primary_key=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"), primary_key=True)
    student_roll_number: Mapped[str] = mapped_column(String(50), primary_key=True)

    student_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Absent")
    check_in_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    qr_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScanLog(Base):
    __tablename__ = "scan_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attendee_email: Mapped[str] = mapped_column(String(100), nullable=False)
    attendee_event_id: Mapped[int] = mapped_column(Integer, nullable=False)
    attendee_roll_number: Mapped[str] = mapped_column(String(50), nullable=False)
    scanned_by_volunteer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    scan_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    scan_result: Mapped[str] = mapped_column(String(50), nullable=False)