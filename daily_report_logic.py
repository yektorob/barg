# daily_report_logic.py
# -*- coding: utf-8 -*-

import os, re, time
import jdatetime
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # Py<3.9

# ================= تنظیمات =================
# Keep only runtime settings that are used.
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tehran")

# Database-backed implementation (no Google Sheets)
from performance_db import PeopleProjectsDB as _PeopleProjectsDB
from daily_report_db import DailyReportDB as _DailyReportDB

# ============== ابزارک‌های کمکی ==============
_ZW = ''.join(['\u200c','\u200f','\u202a','\u202b','\u202c','\u202d','\u202e','\u00a0'])
_P2E = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')

def _norm(s: str) -> str:
    s = str(s or "").strip()
    s = s.translate(_P2E)
    s = re.sub(rf"[{_ZW}]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s

def _now_tz():
    if ZoneInfo is not None:
        return datetime.now(ZoneInfo(TIMEZONE))
    return datetime.now()



def weekday_from_jalali(date_str: str) -> str:
    try:
        y, m, d = map(int, _norm(date_str).split('/'))
        wd = jdatetime.date(y, m, d).togregorian().weekday()  # 0=Mon..6=Sun
        days = ["دوشنبه","سه‌شنبه","چهارشنبه","پنج‌شنبه","جمعه","شنبه","یکشنبه"]
        return days[wd]
    except Exception:
        return ""

def jalali_today_str() -> str:
    # تاریخ جلالی امروز (بدون ساعت) در تایم‌زون تنظیم‌شده
    g = _now_tz().date()
    j = jdatetime.date.fromgregorian(date=g)
    return f"{j.year:04d}/{j.month:02d}/{j.day:02d}"

def jalali_to_greg(date_jalali: str):
    """yyyy/mm/dd جلالی → تاریخ گریگوریان datetime.date"""
    y, m, d = map(int, _norm(date_jalali).split('/'))
    return jdatetime.date(y, m, d).togregorian()

def valid_status(value: str) -> bool:
    return _norm(value) in (_norm("✅ انجام شده"), _norm("❌ انجام نشده"))

# ===== ۱) پر کردن کومبوباکس‌ها از Sheet4 (B=نوع, C=نام) =====
def load_local_data(_: str = None):
    """Return (persons, projects) from the Performance table in DB."""
    try:
        db = _PeopleProjectsDB()
        ppl = db.get_all_people()
        prj = db.get_all_projects()
        persons = [p['name'] for p in ppl]
        projects = [p['name'] for p in prj]
        return sorted(persons), sorted(projects)
    except Exception:
        return [], []

# ===== ۲) نگاشت سرستون‌های Sheet3 (مطابق هدرهای شما) =====
_HEADER_SYNS = {
    "date_gregorian": ["تاریخ میلادی","date_gregorian","gregorian","timestamp"],
    "reporter":       ["نام","reporter","گزارش‌دهنده","گزارش دهنده","نام گزارش‌دهنده"],
    "date_shamsi":    ["تاریخ شمسی","date_shamsi","تاریخ","تاریخ جلالی"],
    "weekday":        ["روز هفته","weekday","روز"],
    "project":        ["نام پروژه","project","پروژه"],
    "task":           ["فعالیت","task","عنوان فعالیت"],
    "status":         ["وضعیت","status"],
    "duration":       ["زمان صرف شده","duration","مدت","مدت زمان","دقیقه"],
    "note":           ["توضیحات","note","یادداشت","توضیح"],
    "performed_by":   ["کار فرد دیگری بوده؟","performed_by"],
    "done_at":        ["وضعیت انجام نشده کی انجام شده؟","done_at","completed_at"],
}

_CANON_HEADERS = [
    "تاریخ میلادی","نام","تاریخ شمسی","روز هفته","نام پروژه",
    "فعالیت","وضعیت","زمان صرف شده","توضیحات","کار فرد دیگری بوده؟","وضعیت انجام نشده کی انجام شده؟"
]

def _header_map(ws):
    vals = ws.get_all_values()
    if not vals:
        ws.append_row(_CANON_HEADERS, value_input_option="USER_ENTERED")
        time.sleep(0.2)
        header = _CANON_HEADERS
    else:
        header = vals[0]
    mp = {}
    for i, h in enumerate(header):
        h0 = _norm(h)
        for key, syns in _HEADER_SYNS.items():
            if h0 in {_norm(s) for s in syns}:
                mp[key] = i
                break
    return mp

# ===== ۳) خواندن اقدامات انجام‌نشده =====
def fetch_unfinished(reporter: str):
    """Return unfinished tasks for a reporter from DB.

    Returns dict with key 'tasks' similar to the old format but without sheet-specific row/col data.
    """
    try:
        db = _DailyReportDB()
        rows = db.get_unfinished_for_reporter(reporter)
        tasks = []
        for r in rows:
            tasks.append({
                "reporter": r.get('reporter',''),
                "date_shamsi": r.get('date_shamsi',''),
                "weekday": r.get('weekday',''),
                "project": r.get('project',''),
                "task": r.get('task',''),
                "status": r.get('status',''),
                "duration": r.get('duration',''),
                "note": r.get('note',''),
                "timestamp": r.get('id'),
                "row": None,
                "status_col": None,
                "done_at_col": None,
            })
        return {"tasks": tasks}
    except Exception:
        return {"tasks": []}

# ===== ۴) تیک «انجام شد» + تاریخ شمسی روز انجام =====
def mark_task_done(timestamp: str, reporter: str, row: int | None = None, status_col: int | None = None, done_at_col: int | None = None):
    """Mark a task as done.

    `timestamp` is now the DB record id if provided; otherwise `reporter` will mark all unfinished.
    """
    try:
        db = _DailyReportDB()
        # if timestamp looks like an id (uuid), treat as single row
        if timestamp and isinstance(timestamp, str) and len(timestamp) >= 8 and '-' in timestamp:
            ok, msg = db.mark_done(record_id=timestamp)
            return ok, msg

        # otherwise mark by reporter
        ok, msg = db.mark_done(reporter=reporter)
        return ok, msg
    except Exception as ex:
        return False, f"خطا در بروزرسانی: {ex}"

# ===== ۵) ارسال گزارش روزانه (با تایید واقعیِ درج) =====
def submit_daily_report(date_jalali: str, weekday_fa: str, reporter: str, tasks: list[dict]):
    """
    تاریخ میلادی = timestamp (Serial) لحظهٔ ارسال.
    done_at پر نمی‌شود مگر بعداً «انجام شد» بخورد.
    performed_by: اگر با reporter برابر نباشد => نام فرد؛ وگرنه 'خیر'.
    """
    try:
        # normalize weekday
        if not _norm(weekday_fa):
            try:
                weekday_fa = weekday_from_jalali(date_jalali)
            except Exception:
                weekday_fa = ""
        db = _DailyReportDB()
        ok, msg = db.submit_bulk(reporter=reporter, date_shamsi=date_jalali, weekday=weekday_fa, tasks=tasks)
        return ok, msg
    except Exception as ex:
        return False, f"خطا در ارسال: {ex}"

# ===== ۶) تاریخ‌های ارسال‌شده‌ی یک گزارش‌دهنده در یک ماه جلالی =====
def fetch_activity_dates(person: str, year_j: int, month_j: int):
    """
    فقط بر اساس «reporter».
    person: نام گزارش‌دهنده
    year_j, month_j: تاریخ جلالی هدف (YYYY, M)
    خروجی: {"dates": ["YYYY/MM/DD", ...]} تاریخ‌های یکتا که این شخص گزارش ارسال کرده
    """
    try:
        db = _DailyReportDB()
        dates = db.fetch_activity_dates(person, year_j, month_j)
        return {"dates": dates}
    except Exception:
        return {"dates": []}


# ===== ۷) خواندن ردیف‌های یک گزارش‌دهنده در یک تاریخ جلالی =====
def fetch_rows_for_reporter_date(reporter: str, date_shamsi: str):
    """Return list of rows (dict) for reporter on date_shamsi (YYYY/MM/DD)."""
    try:
        db = _DailyReportDB()
        rows = db.get_rows_by_reporter_date(reporter, date_shamsi)
        return rows
    except Exception:
        return []


# ===== ۸) بروزرسانی یک ردیف گزارش روزانه =====
def update_daily_report_row(row_id: str, **fields) -> bool:
    try:
        db = _DailyReportDB()
        return db.update_report_row(row_id, **fields)
    except Exception:
        return False
