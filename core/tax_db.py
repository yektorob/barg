"""
Tax dashboard DB layer — CRUD helpers for TaxCompany, TaxActivity, TaxFile.
"""
import json
from typing import Optional, List, Any
from .db import get_session, TaxCompany, TaxActivity, TaxFile


class TaxCompanyDB:
    """CRUD for TaxCompany."""

    @staticmethod
    def create(company_name: str, **kwargs) -> Optional[dict]:
        try:
            sess = get_session()
            with sess.begin():
                company = TaxCompany(company_name=company_name, **kwargs)
                sess.add(company)
            return {
                'id': company.id,
                'company_name': company.company_name,
                'company_code': company.company_code,
            }
        except Exception:
            return None

    @staticmethod
    def get_by_id(company_id: str) -> Optional[dict]:
        try:
            sess = get_session()
            with sess.begin():
                company = sess.get(TaxCompany, company_id)
                if not company:
                    return None
                return {
                    'id': company.id,
                    'company_name': company.company_name,
                    'company_code': company.company_code,
                    'phone': company.phone,
                    'address': company.address,
                    'registration_number': company.registration_number,
                    'national_id': company.national_id,
                    'financial_year_start': company.financial_year_start,
                    'financial_year_end': company.financial_year_end,
                    'tax_id': company.tax_id,
                    'financial_manager': company.financial_manager,
                    'notes': company.notes,
                }
        except Exception:
            return None

    @staticmethod
    def get_all() -> List[dict]:
        try:
            sess = get_session()
            with sess.begin():
                companies = sess.query(TaxCompany).order_by(TaxCompany.created_at.desc()).all()
                return [
                    {
                        'id': c.id,
                        'company_name': c.company_name,
                        'company_code': c.company_code,
                        'phone': c.phone,
                        'address': c.address,
                    }
                    for c in companies
                ]
        except Exception:
            return []

    @staticmethod
    def update(company_id: str, **fields) -> bool:
        try:
            sess = get_session()
            with sess.begin():
                company = sess.get(TaxCompany, company_id)
                if not company:
                    return False
                for k, v in fields.items():
                    if hasattr(company, k):
                        setattr(company, k, v)
                sess.add(company)
            return True
        except Exception:
            return False

    @staticmethod
    def delete(company_id: str) -> bool:
        try:
            sess = get_session()
            with sess.begin():
                company = sess.get(TaxCompany, company_id)
                if not company:
                    return False
                sess.delete(company)
            return True
        except Exception:
            return False


class TaxActivityDB:
    """CRUD for TaxActivity."""

    @staticmethod
    def create(activity_date: str, **kwargs) -> Optional[dict]:
        try:
            sess = get_session()
            with sess.begin():
                activity = TaxActivity(activity_date=activity_date, **kwargs)
                sess.add(activity)
            return {'id': activity.id, 'activity_date': activity.activity_date}
        except Exception:
            return None

    @staticmethod
    def get_by_id(activity_id: str) -> Optional[dict]:
        try:
            sess = get_session()
            with sess.begin():
                activity = sess.get(TaxActivity, activity_id)
                if not activity:
                    return None
                return {
                    'id': activity.id,
                    'activity_date': activity.activity_date,
                    'activity_type': activity.activity_type,
                    'description': activity.description,
                    'responsible': activity.responsible,
                    'company_id': activity.company_id,
                    'status': activity.status,
                    'notes': activity.notes,
                }
        except Exception:
            return None

    @staticmethod
    def get_by_company(company_id: str) -> List[dict]:
        try:
            sess = get_session()
            with sess.begin():
                activities = sess.query(TaxActivity).filter_by(company_id=company_id).order_by(TaxActivity.activity_date.desc()).all()
                return [
                    {
                        'id': a.id,
                        'activity_date': a.activity_date,
                        'activity_type': a.activity_type,
                        'description': a.description,
                        'status': a.status,
                    }
                    for a in activities
                ]
        except Exception:
            return []

    @staticmethod
    def get_all() -> List[dict]:
        try:
            sess = get_session()
            with sess.begin():
                activities = sess.query(TaxActivity).order_by(TaxActivity.activity_date.desc()).all()
                return [
                    {
                        'id': a.id,
                        'activity_date': a.activity_date,
                        'activity_type': a.activity_type,
                        'responsible': a.responsible,
                        'status': a.status,
                    }
                    for a in activities
                ]
        except Exception:
            return []

    @staticmethod
    def update(activity_id: str, **fields) -> bool:
        try:
            sess = get_session()
            with sess.begin():
                activity = sess.get(TaxActivity, activity_id)
                if not activity:
                    return False
                for k, v in fields.items():
                    if hasattr(activity, k):
                        setattr(activity, k, v)
                sess.add(activity)
            return True
        except Exception:
            return False

    @staticmethod
    def delete(activity_id: str) -> bool:
        try:
            sess = get_session()
            with sess.begin():
                activity = sess.get(TaxActivity, activity_id)
                if not activity:
                    return False
                sess.delete(activity)
            return True
        except Exception:
            return False


class TaxFileDB:
    """CRUD for TaxFile."""

    @staticmethod
    def create(company_id: str, file_name: str, **kwargs) -> Optional[dict]:
        try:
            sess = get_session()
            with sess.begin():
                file_obj = TaxFile(company_id=company_id, file_name=file_name, **kwargs)
                sess.add(file_obj)
            return {'id': file_obj.id, 'file_name': file_obj.file_name}
        except Exception:
            return None

    @staticmethod
    def get_by_id(file_id: str) -> Optional[dict]:
        try:
            sess = get_session()
            with sess.begin():
                file_obj = sess.get(TaxFile, file_id)
                if not file_obj:
                    return None
                return {
                    'id': file_obj.id,
                    'company_id': file_obj.company_id,
                    'file_name': file_obj.file_name,
                    'file_path': file_obj.file_path,
                    'file_type': file_obj.file_type,
                    'file_date': file_obj.file_date,
                    'description': file_obj.description,
                    'notes': file_obj.notes,
                }
        except Exception:
            return None

    @staticmethod
    def get_by_company(company_id: str) -> List[dict]:
        try:
            sess = get_session()
            with sess.begin():
                files = sess.query(TaxFile).filter_by(company_id=company_id).order_by(TaxFile.created_at.desc()).all()
                return [
                    {
                        'id': f.id,
                        'file_name': f.file_name,
                        'file_type': f.file_type,
                        'file_date': f.file_date,
                        'description': f.description,
                    }
                    for f in files
                ]
        except Exception:
            return []

    @staticmethod
    def get_all() -> List[dict]:
        try:
            sess = get_session()
            with sess.begin():
                files = sess.query(TaxFile).order_by(TaxFile.created_at.desc()).all()
                return [
                    {
                        'id': f.id,
                        'company_id': f.company_id,
                        'file_name': f.file_name,
                        'file_type': f.file_type,
                    }
                    for f in files
                ]
        except Exception:
            return []

    @staticmethod
    def update(file_id: str, **fields) -> bool:
        try:
            sess = get_session()
            with sess.begin():
                file_obj = sess.get(TaxFile, file_id)
                if not file_obj:
                    return False
                for k, v in fields.items():
                    if hasattr(file_obj, k):
                        setattr(file_obj, k, v)
                sess.add(file_obj)
            return True
        except Exception:
            return False

    @staticmethod
    def delete(file_id: str) -> bool:
        try:
            sess = get_session()
            with sess.begin():
                file_obj = sess.get(TaxFile, file_id)
                if not file_obj:
                    return False
                sess.delete(file_obj)
            return True
        except Exception:
            return False
