# core/db.py
import os
from datetime import datetime
import uuid

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, text, Numeric
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import save_config

Base = declarative_base()
_engine = None
_SessionLocal = None


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(16), nullable=False, default="user")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # لیست دسترسی ماژول‌ها برای هر کاربر (به‌صورت رشته‌ی کاما جدا)
    feature_perms = Column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<User username={self.username!r} role={self.role!r}>"


class Performance(Base):
    """مدل برای ذخیره افراد و پروژه‌ها (Sheet4)"""
    __tablename__ = "performance"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(32), nullable=False, index=True)  # "person" یا "project"
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Performance id={self.id!r} type={self.type!r} name={self.name!r}>"


class PerformanceTarget(Base):
    """مدل برای ذخیره اهداف عملکردی (Sheet5)"""
    __tablename__ = "performance_targets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    person_id = Column(String(36), nullable=False, index=True)  # رفرنس به Performance.id (type='person')
    project_id = Column(String(36), nullable=False, index=True)  # رفرنس به Performance.id (type='project')
    minutes = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<PerformanceTarget person={self.person_id} project={self.project_id} minutes={self.minutes}>"


class DailyReport(Base):
    """مدل برای نگهداری ردیف‌های گزارش روزانه (جایگزین Sheet3)"""
    __tablename__ = "daily_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reporter = Column(String(255), nullable=False, index=True)
    date_shamsi = Column(String(16), nullable=False, index=True)  # YYYY/MM/DD
    weekday = Column(String(32), nullable=True)
    project = Column(String(255), nullable=True, index=True)
    task = Column(String(1024), nullable=True)
    status = Column(String(64), nullable=True)
    duration = Column(Integer, nullable=False, default=0)
    note = Column(String(2000), nullable=True)
    performed_by = Column(String(255), nullable=True)
    done_at = Column(String(16), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DailyReport reporter={self.reporter!r} date={self.date_shamsi!r} task={self.task!r}>"


class AppState(Base):
    """Generic key/value JSON state for small app settings and counters."""
    __tablename__ = "app_state"

    key = Column(String(128), primary_key=True)
    value = Column(String, nullable=True)  # JSON-encoded string
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<AppState {self.key!r}>"


class TaxCompany(Base):
    """Company registration data (tax_apps/app1)."""
    __tablename__ = "tax_companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name = Column(String(255), nullable=False, index=True)
    company_code = Column(String(64), nullable=True, unique=True, index=True)
    phone = Column(String(20), nullable=True)
    address = Column(String(1000), nullable=True)
    registration_number = Column(String(128), nullable=True)
    national_id = Column(String(128), nullable=True)
    financial_year_start = Column(String(16), nullable=True)  # YYYY/MM/DD
    financial_year_end = Column(String(16), nullable=True)    # YYYY/MM/DD
    tax_id = Column(String(128), nullable=True)
    financial_manager = Column(String(255), nullable=True)
    notes = Column(String(2000), nullable=True)
    data_json = Column(String, nullable=True)  # Extra fields as JSON
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<TaxCompany {self.company_name!r} code={self.company_code!r}>"


class TaxActivity(Base):
    """Activities/Actions for tax tracking (tax_apps/app2)."""
    __tablename__ = "tax_activities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    activity_date = Column(String(16), nullable=False, index=True)  # YYYY/MM/DD
    activity_type = Column(String(128), nullable=True)  # Category/type
    description = Column(String(2000), nullable=True)
    responsible = Column(String(255), nullable=True)  # Person responsible
    company_id = Column(String(36), nullable=True, index=True)  # Link to TaxCompany
    status = Column(String(64), nullable=True)  # Status (pending, done, etc.)
    notes = Column(String(2000), nullable=True)
    data_json = Column(String, nullable=True)  # Extra fields as JSON
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<TaxActivity {self.activity_type!r} on {self.activity_date!r}>"


class TaxFile(Base):
    """Tax-related files and documents (tax_apps/app3)."""
    __tablename__ = "tax_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), nullable=False, index=True)  # Link to TaxCompany
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(1000), nullable=True)  # Local file path
    file_type = Column(String(64), nullable=True)  # Category (invoice, report, etc.)
    file_date = Column(String(16), nullable=True)  # YYYY/MM/DD when file was created/relevant
    description = Column(String(1000), nullable=True)
    notes = Column(String(2000), nullable=True)
    data_json = Column(String, nullable=True)  # Extra fields as JSON
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<TaxFile {self.file_name!r} for company_id={self.company_id!r}>"


def _ensure_db_path(config: dict) -> str:
    """
    مسیر فایل دیتابیس رو از config برمی‌داره یا اگر نباشه تنظیم می‌کنه.
    این‌جا فقط آدرس ذخیره میشه، هیچ داده‌ی کاربری تو config نیست.
    """
    db_path = config.get("db_path")
    if not db_path:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        db_path = os.path.join(data_dir, "app.sqlite3")
        config["db_path"] = db_path
        save_config(config)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    return db_path


def _apply_migrations(engine) -> None:
    """
    مایگریشن‌های ساده روی دیتابیس موجود.
    فعلاً فقط مطمئن می‌شیم ستون feature_perms روی جدول users هست.
    """
    try:
        with engine.connect() as conn:
            # اگر ستون از قبل وجود داشته باشه، این دستور خطا می‌ده
            # که ما نادیده می‌گیریم.
            conn.execute(text("ALTER TABLE users ADD COLUMN feature_perms VARCHAR(255)"))
    except Exception:
        # یعنی یا ستون هست، یا نسخه‌ی sqlite قدیمی اذیت کرده؛
        # برای این اپ کافی‌ه.
        pass


def init_db(config: dict):
    """
    دیتابیس رو راه می‌اندازه و جدول‌ها رو می‌سازه، و یه Session برمی‌گردونه.
    """
    global _engine, _SessionLocal

    db_path = _ensure_db_path(config)
    url = f"sqlite:///{db_path}"

    _engine = create_engine(url, echo=False, future=True)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)

    Base.metadata.create_all(_engine)
    _apply_migrations(_engine)

    return _SessionLocal()


def get_session():
    """
    هرجا Session جدید خواستی، از این استفاده کن (بعد از init_db).
    """
    global _SessionLocal
    if _SessionLocal is None:
        raise RuntimeError("Database is not initialized. Call init_db(config) first.")
    return _SessionLocal()