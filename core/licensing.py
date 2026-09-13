from __future__ import annotations

import json
import os
import hmac
import hashlib
from datetime import datetime, date
from typing import List, Dict, Optional

from .config import save_config, BASE_DIR


# ------------------ تعریف همه فیچرها ------------------

ALL_FEATURES: List[Dict] = [
    {"id": "bank_mapper",     "title": "صورتحساب بانکی",   "module": "bank_mapper_page",      "roles": ["admin", "user"]},
    {"id": "reconciliation",  "title": "مغایرت بانکی",     "module": "reconciliation_page",   "roles": ["admin", "user"]},
    {"id": "tax_dashboard",   "title": "داشبورد مالیاتی",  "module": "ui.tax_dashboard_page", "roles": ["admin"]},
    {"id": "ziyafat",         "title": "سپیدز",            "module": "ziyafat_page",          "roles": ["admin", "user"]},
    {"id": "shaparak_sales",  "title": "فروش شاپرکی",      "module": "abbaspoor_page",        "roles": ["admin", "user"]},
    {"id": "seasonal_sales",  "title": "فروش فصلی",        "module": "ffasli_page",           "roles": ["admin", "user"]},
    {"id": "sales",           "title": "فاکتور فروش",      "module": "sales_page",            "roles": ["admin", "user"]},
    {"id": "tejarat_system",  "title": "سامانه تجارت",     "module": "transform_page",        "roles": ["admin", "user"]},
    {"id": "performance",     "title": "گزارش عملکرد",     "module": "performance_page",      "roles": ["admin"]},
    {"id": "daily_report",    "title": "گزارش روزانه",     "module": "daily_report_page",      "roles": ["admin", "user"]},
]

_VALID_FEATURE_IDS = {f["id"] for f in ALL_FEATURES}


# ------------------ تنظیمات لایسنس ------------------

# در محصول واقعی این کلید را قبل از بیلد عوض کن و جایی منتشرش نکن.
# این مقدار فقط برای توسعه است.
_SECRET_KEY = b"CHANGE_THIS_SECRET_KEY"

# مسیر پیش‌فرض فایل لایسنس کنار exe
DEFAULT_LICENSE_PATH = os.path.join(BASE_DIR, "license.json")


class LicenseError(Exception):
    pass


def _canonical_payload_bytes(data: Dict) -> bytes:
    """
    بخش قابل امضا (همه‌ی فیلدها به‌جز signature) را به‌صورت JSON پایدار برمی‌گرداند.
    """
    payload = {k: v for k, v in data.items() if k != "signature"}
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def sign_license_payload(payload: Dict, secret: bytes | str | None = None) -> Dict:
    """
    فقط برای ابزار ساخت لایسنس سمت خودت.

    payload باید شامل حداقل این فیلدها باشد:
      company: str
      features: List[str]
      expires: "YYYY-MM-DD"
      license_id: str
    """
    if secret is None:
        secret = _SECRET_KEY
    if isinstance(secret, str):
        secret = secret.encode("utf-8")

    data = dict(payload)
    data.pop("signature", None)

    if not isinstance(data.get("company"), str) or not data["company"].strip():
        raise ValueError("company is required")
    if not isinstance(data.get("license_id"), str) or not data["license_id"].strip():
        raise ValueError("license_id is required")

    feats = data.get("features")
    if not isinstance(feats, list) or not feats:
        raise ValueError("features must be a non-empty list")
    for f in feats:
        if not isinstance(f, str):
            raise ValueError("features must be list[str]")

    try:
        datetime.strptime(data["expires"], "%Y-%m-%d")
    except Exception as e:
        raise ValueError("expires must be YYYY-MM-DD") from e

    sig = hmac.new(secret, _canonical_payload_bytes(data), hashlib.sha256).hexdigest()
    data["signature"] = sig
    return data


def _verify_signature(data: Dict, secret: bytes | str | None = None) -> None:
    if secret is None:
        secret = _SECRET_KEY
    if isinstance(secret, str):
        secret = secret.encode("utf-8")

    sig = data.get("signature")
    if not isinstance(sig, str) or not sig:
        raise LicenseError("signature is missing")

    expected = hmac.new(secret, _canonical_payload_bytes(data), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise LicenseError("invalid signature")


def _parse_date(d: str) -> date:
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except Exception as e:
        raise LicenseError("invalid date format (expected YYYY-MM-DD)") from e


def load_and_verify_license_from_file(path: str) -> Dict:
    """
    فایل لایسنس را می‌خواند، امضا و تاریخ انقضا را چک می‌کند.
    در صورت مشکل، LicenseError می‌اندازد.
    """
    if not os.path.exists(path):
        raise LicenseError(f"license file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise LicenseError(f"cannot read license file: {e}") from e

    if not isinstance(data, dict):
        raise LicenseError("license file must contain a JSON object")

    _verify_signature(data)

    expires_s = data.get("expires")
    if not isinstance(expires_s, str):
        raise LicenseError("expires field is missing")
    expires = _parse_date(expires_s)
    if expires < date.today():
        raise LicenseError("license has expired")

    feats = data.get("features")
    if not isinstance(feats, list) or not feats:
        raise LicenseError("features list is empty")
    feats = [f for f in feats if isinstance(f, str)]

    data["features"] = feats
    return data


def _features_from_license_dict(lic: Dict) -> List[str]:
    # internal helper
    feats = lic.get("features") or []
    return sorted({f for f in feats if f in _VALID_FEATURE_IDS})


def features_from_license_dict(lic: Dict) -> List[str]:
    """
    نسخه‌ی public برای استفاده در UI (مثلاً پیش‌نمایش لایسنس).
    """
    return _features_from_license_dict(lic)


def apply_license(config: dict, *, license_path: str, license_dict: Optional[Dict] = None) -> List[str]:
    """
    لایسنس داده‌شده را روی config اعمال می‌کند:
      - path را ذخیره می‌کند
      - features معتبر را در enabled_features می‌نویسد
      - در نهایت config.json را ذخیره می‌کند
    """
    if license_dict is None:
        license_dict = load_and_verify_license_from_file(license_path)

    enabled = _features_from_license_dict(license_dict)
    if not enabled:
        raise LicenseError("no valid features in license")

    config["license_path"] = os.path.abspath(license_path)
    config["enabled_features"] = enabled
    save_config(config)
    return enabled


def read_current_license_info(config: dict) -> Dict:
    """
    برای UI: وضعیت فعلی لایسنس را برمی‌گرداند.
    نتیجه مثل زیر است:
      {"status": "missing" | "invalid" | "ok", ...}
    """
    path = config.get("license_path") or DEFAULT_LICENSE_PATH
    info: Dict = {"path": path}

    if not path or not os.path.exists(path):
        info["status"] = "missing"
        return info

    try:
        lic = load_and_verify_license_from_file(path)
    except Exception as e:
        info["status"] = "invalid"
        info["error"] = str(e)
        return info

    feats = _features_from_license_dict(lic)
    info.update(
        {
            "status": "ok",
            "company": lic.get("company", ""),
            "license_id": lic.get("license_id", ""),
            "expires": lic.get("expires", ""),
            "features": feats,
        }
    )
    return info


def ensure_enabled_features(config: dict) -> List[str]:
    """
    مشخص می‌کند این نصب، کدام فیچرها را از نظر لایسنس فعال دارد.

    رفتار جدید (سخت‌گیرانه):

      - اگر license_path در config تنظیم شده باشد:
            * اگر فایل وجود نداشته باشد → هیچ فیچری فعال نیست.
            * اگر فایل وجود داشته باشد ولی امضا/تاریخش مشکل داشته باشد → هیچ فیچری فعال نیست.
            * اگر معتبر باشد → فقط فیچرهای داخل لایسنس فعال می‌شوند.

      - اگر license_path اصلاً تنظیم نشده باشد (حالت dev / قدیمی):
            * اگر enabled_features قبلاً در config بود → همان، بعد از تمیزکردن.
            * اگر نبود → همه فیچرها فعال (فقط برای توسعه).
    """
    enabled: Optional[List[str]] = None
    license_path = config.get("license_path")

    if license_path:
        # وقتی لایسنس تنظیم شده، هر گونه مشکل = صفر فیچر
        if not os.path.exists(license_path):
            enabled = []
        else:
            try:
                lic = load_and_verify_license_from_file(license_path)
                enabled = _features_from_license_dict(lic)
            except Exception:
                enabled = []

    if enabled is None:
        # یعنی license_path تنظیم نشده (حالت dev/قدیمی)
        existing = config.get("enabled_features")
        if isinstance(existing, list):
            enabled = [fid for fid in existing if fid in _VALID_FEATURE_IDS]
        else:
            # در حالت production: اگر فایل لایسنس تنظیم نشده، هیچ فیچری فعال نیست.
            enabled = []

    config["enabled_features"] = enabled
    save_config(config)
    return enabled