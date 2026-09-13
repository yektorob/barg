from datetime import date, timedelta
import json
from core.licensing import sign_license_payload  # مسیر رو طبق پکیج خودت تنظیم کن


def make_license(
    company: str,
    license_id: str,
    features: list[str],
    days_valid: int = 365,
    out_path: str = "license.json",
):
    payload = {
        "company": company,
        "license_id": license_id,
        "features": features,
        "expires": (date.today() + timedelta(days=days_valid)).strftime("%Y-%m-%d"),
    }

    lic = sign_license_payload(payload)  # از همون _SECRET_KEY داخل licensing.py استفاده می‌کنه

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(lic, f, ensure_ascii=False, indent=2)
    print(f"License written to {out_path}")


if __name__ == "__main__":
    # اینجا هر چی خواستی تست کنی:
    make_license(
        company="شرکت تستی",
        license_id="LIC-TEST-0002",
        features=[
            "bank_mapper",
            "reconciliation",
            "shaparak_sales",       
            "seasonal_sales",
            "tejarat_system",
            "performance",
            "daily_report",
            "sales",
            "tax_dashboard",
            "ziyafat" 
                # ← مثلا همون ماژول جدیدی که اضافه کردی
        ],
        days_valid=365,
        out_path="license_test.json",
    )