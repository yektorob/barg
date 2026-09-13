import sys

from .ui.qt import QtWidgets
from .core.config import load_config
from .core.licensing import ensure_enabled_features
from .core.db import init_db
from .ui.dialogs import ensure_initial_admin_user, login_and_get_user
from .ui.main_window import Suite
from .ui.style import apply_qss


def main():
    app = QtWidgets.QApplication(sys.argv)
    apply_qss(app)

    # ۱) لود تنظیمات عمومی (غیرکاربری)
    config = load_config()

    # ۲) راه‌اندازی دیتابیس و گرفتن یک Session
    session = init_db(config)

    # ۳) اگر هیچ کاربری نداریم، ادمین اولیه را بساز (روی DB)
    ensure_initial_admin_user(session)

    # ۴) فعال‌سازی لیست ماژول‌های قابل استفاده برای این نصب
    enabled_features = ensure_enabled_features(config)

    # ۵) لاگین کاربر (هر کاربر با پسورد خودش از دیتابیس)
    current_user = login_and_get_user(session)
    if not current_user:
        sys.exit(0)

    w = Suite(current_user=current_user, config=config, enabled_features=enabled_features)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()