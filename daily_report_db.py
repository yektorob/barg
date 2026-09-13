# daily_report_db.py
"""
Database layer for daily reports. Stores individual report rows in `daily_reports` table.
"""
from __future__ import annotations
import uuid
from typing import List, Dict, Optional
from datetime import datetime

from core.db import DailyReport, get_session
from sqlalchemy import or_


class DailyReportDB:
    def __init__(self, session=None):
        self.session = session

    def _get_session(self):
        if self.session is not None:
            return self.session
        return get_session()

    def add_report_row(self, reporter: str, date_shamsi: str, weekday: str, project: str,
                       task: str, status: str, duration: int, note: str, performed_by: str) -> str:
        sess = self._get_session()
        dr = DailyReport(
            id=str(uuid.uuid4()),
            reporter=reporter,
            date_shamsi=date_shamsi,
            weekday=weekday,
            project=project,
            task=task,
            status=status,
            duration=int(duration or 0),
            note=note,
            performed_by=performed_by,
            done_at=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        sess.add(dr)
        sess.commit()
        return dr.id

    def get_unfinished_for_reporter(self, reporter: str) -> List[Dict]:
        sess = self._get_session()
        # match either explicit ❌ emoji or the Persian phrase 'انجام نشده'
        rows = sess.query(DailyReport).filter(
            DailyReport.reporter == reporter
        ).filter(
            or_(DailyReport.status.contains('❌'), DailyReport.status.ilike('%انجام نشده%'))
        ).all()
        return [
            {
                "id": r.id,
                "reporter": r.reporter,
                "date_shamsi": r.date_shamsi,
                "weekday": r.weekday,
                "project": r.project,
                "task": r.task,
                "status": r.status,
                "duration": r.duration,
                "note": r.note,
                "performed_by": r.performed_by,
                "done_at": r.done_at,
            }
            for r in rows
        ]

    def mark_done(self, record_id: Optional[str] = None, reporter: Optional[str] = None) -> (bool, str):
        sess = self._get_session()
        updated = 0
        now_j = None
        try:
            import jdatetime
            now_j = jdatetime.date.today().strftime('%Y/%m/%d')
        except Exception:
            now_j = None

        if record_id:
            r = sess.query(DailyReport).filter(DailyReport.id == record_id).first()
            if not r:
                return False, "ردیف پیدا نشد"
            r.status = '✅ انجام شده'
            if now_j:
                r.done_at = now_j
            sess.commit()
            return True, "با موفقیت ثبت شد."

        if reporter:
            rows = sess.query(DailyReport).filter(
                DailyReport.reporter == reporter
            ).filter(
                or_(DailyReport.status.contains('❌'), DailyReport.status.ilike('%انجام نشده%'))
            ).all()
            for r in rows:
                r.status = '✅ انجام شده'
                if now_j:
                    r.done_at = now_j
                updated += 1
            sess.commit()
            if updated:
                return True, "با موفقیت ثبت شد."
            return False, "موردی برای تغییر پیدا نشد."

        return False, "پارامتر معتبر نیست"

    def submit_bulk(self, reporter: str, date_shamsi: str, weekday: str, tasks: List[Dict]) -> (bool, str):
        if not tasks:
            return False, "آیتمی برای ارسال وجود ندارد."
        sess = self._get_session()
        before = sess.query(DailyReport).count()
        for t in tasks:
            self.add_report_row(
                reporter=reporter,
                date_shamsi=date_shamsi,
                weekday=weekday,
                project=t.get('project',''),
                task=t.get('task',''),
                status=t.get('status','') or '❌ انجام نشده',
                duration=int(t.get('duration') or 0),
                note=t.get('note',''),
                performed_by=t.get('performed_by', reporter),
            )
        after = sess.query(DailyReport).count()
        if after - before == len(tasks):
            return True, '✅ ارسال شد.'
        return False, 'ارسال تایید نشد؛ دوباره تلاش کنید.'

    def fetch_activity_dates(self, reporter: str, year_j: int, month_j: int) -> List[str]:
        sess = self._get_session()
        rows = sess.query(DailyReport).filter(DailyReport.reporter == reporter).all()
        seen = set()
        for r in rows:
            ds = (r.date_shamsi or "").strip()
            if not ds:
                continue
            try:
                parts = ds.split('/')
                y = int(parts[0]); m = int(parts[1])
            except Exception:
                continue
            if y == year_j and m == month_j:
                seen.add(ds)
        return sorted(seen, reverse=True)

    def get_rows_by_reporter_date(self, reporter: str, date_shamsi: str) -> List[Dict]:
        """Return all rows for reporter on given Jalali date string (YYYY/MM/DD)."""
        sess = self._get_session()
        rows = sess.query(DailyReport).filter(
            DailyReport.reporter == reporter,
            DailyReport.date_shamsi == (date_shamsi or "")
        ).order_by(DailyReport.created_at.asc()).all()
        return [
            {
                "id": r.id,
                "reporter": r.reporter,
                "date_shamsi": r.date_shamsi,
                "weekday": r.weekday,
                "project": r.project,
                "task": r.task,
                "status": r.status,
                "duration": r.duration,
                "note": r.note,
                "performed_by": r.performed_by,
                "done_at": r.done_at,
            }
            for r in rows
        ]

    def update_report_row(self, row_id: str, **fields) -> bool:
        """Update a report row by id. Allowed fields: date_shamsi, weekday, project, task, status, duration, note, performed_by."""
        sess = self._get_session()
        r = sess.query(DailyReport).filter(DailyReport.id == row_id).first()
        if not r:
            return False
        allowed = {"date_shamsi","weekday","project","task","status","duration","note","performed_by","done_at"}
        updated = False
        for k, v in fields.items():
            if k in allowed:
                setattr(r, k, v)
                updated = True
        if updated:
            r.updated_at = datetime.utcnow()
            sess.commit()
            return True
        return False
