import os
import sys
import json

# مسیر پایه برنامه (برای پیدا کردن config.json)
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


def load_config() -> dict:
    """
    تنظیمات برنامه را از فایل config.json می‌خواند.
    اگر فایل وجود نداشته باشد یا خراب باشد، دیکشنری خالی برمی‌گرداند.
    """
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def save_config(cfg: dict) -> None:
    """
    تنظیمات را در فایل config.json ذخیره می‌کند.
    """
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        # در محصول واقعی بهتر است لاگ بنویسی
        pass