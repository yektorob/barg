"""
Tax apps logic wrappers — replaces Google Sheets calls with DB-backed functions.
Provides compatible API for app1 (companies), app2 (activities), app3 (files).
"""
import json
from typing import List, Optional, Dict, Any
from core.tax_db import TaxCompanyDB, TaxActivityDB, TaxFileDB


# ============ COMPANY FUNCTIONS (app1) ============

def load_companies() -> List[Dict[str, Any]]:
    """Load all companies from DB."""
    return TaxCompanyDB.get_all()


def get_company(company_id: str) -> Optional[Dict[str, Any]]:
    """Get company by ID."""
    return TaxCompanyDB.get_by_id(company_id)


def save_company(company_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Save company (insert or update).
    If 'id' exists, update; otherwise create new.
    """
    company_id = company_data.get('id')
    company_name = company_data.get('company_name', '')

    if company_id:
        # Update existing
        success = TaxCompanyDB.update(company_id, **company_data)
        if success:
            return TaxCompanyDB.get_by_id(company_id)
        return None
    else:
        # Create new
        return TaxCompanyDB.create(company_name=company_name, **company_data)


def delete_company(company_id: str) -> bool:
    """Delete company."""
    return TaxCompanyDB.delete(company_id)


# ============ ACTIVITY FUNCTIONS (app2) ============

def load_activities(company_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load activities.
    If company_id provided, return activities for that company; otherwise all.
    """
    if company_id:
        return TaxActivityDB.get_by_company(company_id)
    return TaxActivityDB.get_all()


def get_activity(activity_id: str) -> Optional[Dict[str, Any]]:
    """Get activity by ID."""
    return TaxActivityDB.get_by_id(activity_id)


def save_activity(activity_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Save activity (insert or update).
    If 'id' exists, update; otherwise create new.
    """
    activity_id = activity_data.get('id')
    activity_date = activity_data.get('activity_date', '')

    if activity_id:
        # Update
        success = TaxActivityDB.update(activity_id, **activity_data)
        if success:
            return TaxActivityDB.get_by_id(activity_id)
        return None
    else:
        # Create new
        return TaxActivityDB.create(activity_date=activity_date, **activity_data)


def delete_activity(activity_id: str) -> bool:
    """Delete activity."""
    return TaxActivityDB.delete(activity_id)


# ============ FILE FUNCTIONS (app3) ============

def load_files(company_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load files.
    If company_id provided, return files for that company; otherwise all.
    """
    if company_id:
        return TaxFileDB.get_by_company(company_id)
    return TaxFileDB.get_all()


def get_file(file_id: str) -> Optional[Dict[str, Any]]:
    """Get file by ID."""
    return TaxFileDB.get_by_id(file_id)


def save_file(file_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Save file (insert or update).
    If 'id' exists, update; otherwise create new.
    """
    file_id = file_data.get('id')
    company_id = file_data.get('company_id', '')
    file_name = file_data.get('file_name', '')

    if file_id:
        # Update
        success = TaxFileDB.update(file_id, **file_data)
        if success:
            return TaxFileDB.get_by_id(file_id)
        return None
    else:
        # Create new
        return TaxFileDB.create(company_id=company_id, file_name=file_name, **file_data)


def delete_file(file_id: str) -> bool:
    """Delete file."""
    return TaxFileDB.delete(file_id)
