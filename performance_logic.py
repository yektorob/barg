# performance_logic.py
# -*- coding: utf-8 -*-
"""
منطق عملکردی - استفاده از دیتابیس SQLite به جای Google Sheets
- Sheet4 (افراد/پروژه‌ها) → Performance table
- Sheet5 (اهداف) → PerformanceTarget table
"""
from __future__ import annotations
import os
import uuid
from typing import List, Dict, Optional, Tuple

from performance_db import PeopleProjectsDB, TargetsDB


# Aliases برای سازگاری با کد موجود
class PeopleProjectsSheet:
    """جایگزین GSheetBase برای افراد و پروژه‌ها"""
    
    def __init__(self, *args, **kwargs):
        """سازنده برای سازگاری با کد قدیم (arguments نادیده گرفته می‌شوند)"""
        self._db = PeopleProjectsDB()
    
    def list_all(self) -> Tuple[List[Tuple[str,str]], List[Tuple[str,str]]]:
        """return: (persons[(id,name)], projects[(id,name)])"""
        people = self._db.get_all_people()
        projects = self._db.get_all_projects()
        
        persons = [(p["id"], p["name"]) for p in people]
        projects_list = [(p["id"], p["name"]) for p in projects]
        
        return persons, projects_list
    
    def add_name(self, kind: str, name: str) -> str:
        """افزودن یک فرد یا پروژه جدید"""
        if kind not in ("person", "project"):
            raise ValueError("kind نامعتبر است.")
        name = (name or "").strip()
        if not name:
            raise ValueError("نام خالی است.")
        
        if kind == "person":
            return self._db.add_person(name)
        else:
            return self._db.add_project(name)
    
    def edit_name(self, rec_id: str, new_name: str) -> bool:
        """ویرایش نام یک فرد یا پروژه"""
        return self._db.update_name(rec_id, new_name)
    
    def delete_name(self, rec_id: str) -> bool:
        """حذف یک فرد یا پروژه"""
        return self._db.delete_by_id(rec_id)


# ---------- Sheet5: اهداف ----------
class TargetsSheet:
    """جایگزین GSheetBase برای اهداف"""
    
    def __init__(self, *args, **kwargs):
        """سازنده برای سازگاری با کد قدیم (arguments نادیده گرفته می‌شوند)"""
        self._db = TargetsDB()
    
    def list_all(self) -> List[Dict[str, object]]:
        """دریافت تمام اهداف"""
        targets = self._db.get_all_targets()
        return [
            {
                "id": t["id"],
                "person": t["person"],
                "project": t["project"],
                "minutes": t["minutes"],
            }
            for t in targets
        ]
    
    def add_target(self, person: str, project: str, minutes: int) -> str:
        """افزودن یک هدف جدید"""
        person = (person or "").strip()
        project = (project or "").strip()
        minutes = int(minutes or 0)
        if not person or not project:
            raise ValueError("person/project خالی است.")
        
        return self._db.add_target(person, project, minutes)
    
    def edit_target(self, rec_id: str, person: str, project: str, minutes: int) -> bool:
        """ویرایش هدف (حالا فقط minutes قابل تغییر است)"""
        minutes = int(minutes or 0)
        return self._db.update_target(rec_id, minutes)
    
    def delete_target(self, rec_id: str) -> bool:
        """حذف یک هدف"""
        return self._db.delete_target(rec_id)
