# performance_db.py
"""
لایهٔ دیتابیسی برای داده‌های عملکردی
- جایگزین Google Sheets (Sheet4 و Sheet5)
- استفاده از SQLAlchemy ORM و دیتابیس SQLite
"""
from __future__ import annotations
import uuid
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from core.db import Performance, PerformanceTarget, get_session


class PeopleProjectsDB:
    """
    مدیریت افراد و پروژه‌ها (جایگزین Sheet4)
    """
    
    def __init__(self, session: Optional[Session] = None):
        self.session = session
    
    def _get_session(self) -> Session:
        """گرفتن session اگر تنظیم نشده باشد"""
        if self.session is None:
            try:
                return get_session()
            except RuntimeError:
                # دیتابیس هنوز راه‌اندازی نشده
                return None
        return self.session
    
    def add_person(self, name: str) -> str:
        """اضافه کردن یک فرد جدید، برگرداندن ID"""
        session = self._get_session()
        perf = Performance(id=str(uuid.uuid4()), type="person", name=name)
        session.add(perf)
        session.commit()
        return perf.id
    
    def add_project(self, name: str) -> str:
        """اضافه کردن یک پروژه جدید، برگرداندن ID"""
        session = self._get_session()
        perf = Performance(id=str(uuid.uuid4()), type="project", name=name)
        session.add(perf)
        session.commit()
        return perf.id
    
    def get_all_people(self) -> List[Dict]:
        """دریافت تمام افراد"""
        session = self._get_session()
        people = session.query(Performance).filter(Performance.type == "person").order_by(Performance.name).all()
        return [
            {"id": p.id, "type": "person", "name": p.name}
            for p in people
        ]
    
    def get_all_projects(self) -> List[Dict]:
        """دریافت تمام پروژه‌ها"""
        session = self._get_session()
        projects = session.query(Performance).filter(Performance.type == "project").order_by(Performance.name).all()
        return [
            {"id": p.id, "type": "project", "name": p.name}
            for p in projects
        ]
    
    def get_person_by_name(self, name: str) -> Optional[Dict]:
        """یافتن یک فرد با نام"""
        session = self._get_session()
        p = session.query(Performance).filter(
            Performance.type == "person",
            Performance.name == name
        ).first()
        if p:
            return {"id": p.id, "type": "person", "name": p.name}
        return None
    
    def get_project_by_name(self, name: str) -> Optional[Dict]:
        """یافتن یک پروژه با نام"""
        session = self._get_session()
        p = session.query(Performance).filter(
            Performance.type == "project",
            Performance.name == name
        ).first()
        if p:
            return {"id": p.id, "type": "project", "name": p.name}
        return None
    
    def get_by_id(self, rec_id: str) -> Optional[Dict]:
        """یافتن رکورد با ID"""
        session = self._get_session()
        p = session.query(Performance).filter(Performance.id == rec_id).first()
        if p:
            return {"id": p.id, "type": p.type, "name": p.name}
        return None
    
    def update_name(self, rec_id: str, new_name: str) -> bool:
        """بروزرسانی نام رکورد"""
        session = self._get_session()
        p = session.query(Performance).filter(Performance.id == rec_id).first()
        if p:
            p.name = new_name
            p.updated_at = datetime.utcnow()
            session.commit()
            return True
        return False
    
    def delete_by_id(self, rec_id: str) -> bool:
        """حذف رکورد"""
        session = self._get_session()
        p = session.query(Performance).filter(Performance.id == rec_id).first()
        if p:
            session.delete(p)
            session.commit()
            return True
        return False


class TargetsDB:
    """
    مدیریت اهداف عملکردی (جایگزین Sheet5)
    """
    
    def __init__(self, session: Optional[Session] = None):
        self.session = session
    
    def _get_session(self) -> Session:
        """گرفتن session اگر تنظیم نشده باشد"""
        if self.session is None:
            try:
                return get_session()
            except RuntimeError:
                # دیتابیس هنوز راه‌اندازی نشده
                return None
        return self.session
    
    def add_target(self, person_id: str, project_id: str, minutes: int) -> str:
        """اضافه کردن یک هدف جدید"""
        session = self._get_session()
        target = PerformanceTarget(
            id=str(uuid.uuid4()),
            person_id=person_id,
            project_id=project_id,
            minutes=minutes
        )
        session.add(target)
        session.commit()
        return target.id
    
    def get_target_by_id(self, target_id: str) -> Optional[Dict]:
        """یافتن یک هدف با ID"""
        session = self._get_session()
        t = session.query(PerformanceTarget).filter(PerformanceTarget.id == target_id).first()
        if t:
            return {
                "id": t.id,
                "person": t.person_id,
                "project": t.project_id,
                "minutes": t.minutes
            }
        return None
    
    def get_target_by_person_project(self, person_id: str, project_id: str) -> Optional[Dict]:
        """یافتن هدفی برای یک فرد و پروژه خاص"""
        session = self._get_session()
        t = session.query(PerformanceTarget).filter(
            PerformanceTarget.person_id == person_id,
            PerformanceTarget.project_id == project_id
        ).first()
        if t:
            return {
                "id": t.id,
                "person": t.person_id,
                "project": t.project_id,
                "minutes": t.minutes
            }
        return None
    
    def get_all_targets(self) -> List[Dict]:
        """دریافت تمام اهداف"""
        session = self._get_session()
        targets = session.query(PerformanceTarget).all()
        return [
            {
                "id": t.id,
                "person": t.person_id,
                "project": t.project_id,
                "minutes": t.minutes
            }
            for t in targets
        ]
    
    def update_target(self, target_id: str, minutes: int) -> bool:
        """بروزرسانی تعداد دقایق یک هدف"""
        session = self._get_session()
        t = session.query(PerformanceTarget).filter(PerformanceTarget.id == target_id).first()
        if t:
            t.minutes = minutes
            t.updated_at = datetime.utcnow()
            session.commit()
            return True
        return False
    
    def delete_target(self, target_id: str) -> bool:
        """حذف یک هدف"""
        session = self._get_session()
        t = session.query(PerformanceTarget).filter(PerformanceTarget.id == target_id).first()
        if t:
            session.delete(t)
            session.commit()
            return True
        return False
    
    def delete_targets_by_person_or_project(self, rec_id: str) -> int:
        """حذف تمام اهداف که از یک فرد یا پروژه حذف شده‌اند"""
        session = self._get_session()
        count = session.query(PerformanceTarget).filter(
            (PerformanceTarget.person_id == rec_id) | (PerformanceTarget.project_id == rec_id)
        ).delete()
        session.commit()
        return count
