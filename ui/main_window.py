from typing import List, Dict

from .qt import QtWidgets, QtGui, QtCore, Sig
from .style import fix_item_views_colors
from .dialogs import LicenseDialog, ManageUsersDialog
from .plugins import load_page_widget
from ..core import licensing
from ..core.config import save_config
from ..core.db import get_session

class NavButton(QtWidgets.QPushButton):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.setMinimumHeight(44)


class SideMenu(QtWidgets.QWidget):
    changed = Sig(int)
    IND_W = 4

    def __init__(self, entries, parent=None):
        super().__init__(parent)
        self.entries = entries
        self.btns: List[NavButton] = []
        self.cur_idx = -1

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.ind = QtWidgets.QFrame()
        self.ind.setFixedWidth(self.IND_W)
        self.ind.setStyleSheet("background-color: #2f7ed8; border-radius: 2px;")
        self.ind.hide()

        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self.ind)
        col = QtWidgets.QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        row.addLayout(col, 1)

        for title, _mod in entries:
            b = NavButton(title, self)
            idx = len(self.btns)
            b.clicked.connect(lambda checked=False, i=idx: self._on(i))
            col.addWidget(b)
            self.btns.append(b)

        col.addStretch(1)
        root.addLayout(row, 1)

        self.anim = QtCore.QPropertyAnimation(self.ind, b"pos")
        self.anim.setDuration(150)
        self.anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

        QtCore.QTimer.singleShot(0, lambda: self._on(0))

    def _on(self, idx: int):
        if not (0 <= idx < len(self.btns)):
            return
        if idx == self.cur_idx:
            return

        for i, b in enumerate(self.btns):
            b.setChecked(i == idx)
        self.cur_idx = idx
        self._move_indicator(idx, animate=True)
        self.changed.emit(idx)

    def _move_indicator(self, idx: int, animate: bool):
        btn = self.btns[idx]
        local_top_right = QtCore.QPoint(btn.width() - self.IND_W, 0)
        pos_in_self = btn.mapTo(self, local_top_right)

        self.ind.setFixedHeight(btn.height())
        self.ind.raise_()
        if not self.ind.isVisible():
            self.ind.show()
            self.ind.move(pos_in_self)
            return

        if animate:
            self.anim.stop()
            self.anim.setStartValue(self.ind.pos())
            self.anim.setEndValue(pos_in_self)
            self.anim.start()
        else:
            self.ind.move(pos_in_self)


class Suite(QtWidgets.QMainWindow):
    def __init__(self, current_user: Dict, config: dict, enabled_features: List[str]):
        super().__init__()
        # داخل __init__ Suite
        self.current_user = current_user
        self.config = config
        self.enabled_features = enabled_features or []
        self.licensed_features = set(self.enabled_features or [])
        self.user_features = set(current_user.get("features") or [])

        # ماژول‌های نهایی که این کاربر می‌بیند:
        self.effective_features = sorted(self.licensed_features & self.user_features)

        # و اگر می‌خوای برای ادمین محدودیت کاربری نذاری:
        if self.current_user["role"] == "admin" and not self.user_features:
            # یعنی برای ادمین چیزی تنظیم نشده -> همه‌ی لایسنس‌ها
            self.effective_features = sorted(self.licensed_features)

        role = self.current_user.get("role", "user")
        self.setWindowTitle(f"Shahr Suite - {role}")
        self.resize(1200, 760)
        self.setLayoutDirection(QtCore.Qt.LeftToRight)  # یکپارچگی: ساید‌بار همیشه در سمت چپ

        # فیچرهای مجاز برای این کاربر (با توجه به لایسنس نصب و دسترسی کاربر و نقش)
        # `self.effective_features` قبلاً بر اساس لایسنس و دسترسی کاربر محاسبه شده.
        eff_set = set(self.effective_features)
        allowed_ids = {f["id"] for f in licensing.ALL_FEATURES if f["id"] in eff_set and role in f["roles"]}
        self.features = [f for f in licensing.ALL_FEATURES if f["id"] in allowed_ids]

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        h = QtWidgets.QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        self.stack = QtWidgets.QStackedWidget()
        h.addWidget(self.stack, 1)

        # اگر هیچ فیچری برای نمایش وجود ندارد، یک پیغام واضح به کاربر نشان بده
        if not self.features:
            info_w = QtWidgets.QWidget()
            v = QtWidgets.QVBoxLayout(info_w)
            v.setContentsMargins(0, 0, 0, 0)

            lbl = QtWidgets.QLabel()
            lbl.setWordWrap(True)

            # نمایش وضعیت لایسنس
            lic_info = licensing.read_current_license_info(self.config)
            if lic_info.get("status") == "missing":
                txt = (
                    "فایل لایسنس برای این شرکت تنظیم نشده است.\n"
                    "لطفاً فایل لایسنس معتبر را آپلود کنید تا ماژول‌ها فعال شوند."
                )
            elif lic_info.get("status") == "invalid":
                txt = (
                    "لایسنس موجود نامعتبر یا منقضی شده است:\n"
                    f"{lic_info.get('error','')}.\nلطفاً فایل لایسنس معتبر را آپلود کنید."
                )
            else:
                txt = (
                    "فعلاً هیچ ماژولی برای این کاربر فعال نیست.\n"
                    "لطفاً لایسنس را بررسی یا آپلود کنید."
                )
            lbl.setText(txt)
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setStyleSheet("color: #555; font-size: 13px; line-height: 1.6;")

            # کارت برای نمایش پیغام
            card = QtWidgets.QFrame()
            card.setStyleSheet(
                "QFrame { background-color: #f5f5f5; border: 1px solid #ddd; "
                "border-radius: 10px; padding: 24px; }"
            )
            card_lay = QtWidgets.QVBoxLayout(card)
            card_lay.setContentsMargins(20, 20, 20, 20)
            card_lay.setSpacing(16)

            btn = QtWidgets.QPushButton("مدیریت لایسنس", self)
            btn.setMaximumWidth(160)
            btn.setMinimumHeight(36)
            btn.clicked.connect(self._open_license_dialog)

            card_lay.addWidget(lbl)
            card_lay.addWidget(btn, 0, QtCore.Qt.AlignCenter)

            # قرار دادن کارت در مرکز صفحه
            h_center = QtWidgets.QHBoxLayout()
            h_center.addStretch(1)
            h_center.addWidget(card)
            h_center.addStretch(1)

            v.addStretch(1)
            v.addLayout(h_center)
            v.addStretch(1)

            self.stack.addWidget(info_w)
            self.stack.setCurrentWidget(info_w)
            self.menu = None  # هیچ منو نمایش داده نمی‌شود
        else:
            # آپلود صفحه‌ها برای ماژول‌های فعال
            entries = [(f["title"], f["module"]) for f in self.features]
            self.menu = SideMenu(entries)
            self.menu.setFixedWidth(240)
            h.addWidget(self.menu, 0)

            for feat in self.features:
                self.stack.addWidget(load_page_widget(feat["module"]))

        fix_item_views_colors(self)

        self._last_idx = 0
        self._pw_restore = False
        if self.menu:
            self.menu.changed.connect(self._on_menu_change)

        # شورتکات مدیریت لایسنس: Ctrl+L (فقط برای ادمین)
        self.lic_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+L"), self)
        self.lic_shortcut.activated.connect(self._open_license_dialog)

        # شورتکات مدیریت کاربران: Ctrl+U (فقط برای ادمین)
        self.users_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+U"), self)
        self.users_shortcut.activated.connect(self._open_users_dialog)
        if self.current_user.get("role") == "admin":
            self._setup_admin_settings_button()

    def _setup_admin_settings_button(self):
        # مثلا در نوار ابزار بالا
        toolbar = getattr(self, "toolbar", None)
        if toolbar is None:
            toolbar = QtWidgets.QToolBar("Main", self)
            self.addToolBar(toolbar)
            self.toolbar = toolbar

        btn = QtWidgets.QToolButton(self)
        btn.setText("تنظیمات")
        btn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)

        menu = QtWidgets.QMenu(self)
        act_users = menu.addAction("مدیریت کاربران")
        act_license = menu.addAction("مدیریت لایسنس")

        act_users.triggered.connect(self._on_manage_users)
        act_license.triggered.connect(self._on_manage_license)

        btn.setMenu(menu)
        toolbar.addWidget(btn)

    def _on_manage_users(self):
        session = get_session()
        dlg = ManageUsersDialog(self, session=session, enabled_features=self.enabled_features)
        dlg.exec()

    def _on_manage_license(self):
        dlg = LicenseDialog(self, current_enabled=self.enabled_features, config=self.config)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            res = dlg.get_result()
            if res and res.get("enabled_ids"):
                # لایسنس جدید اعمال شده و config هم توی licensing.apply_license ذخیره شده
                self.enabled_features = res["enabled_ids"]
                QtWidgets.QMessageBox.information(
                    self,
                    "لایسنس ثبت شد",
                    "لایسنس جدید ثبت شد.\nبرای اعمال کامل تغییرات بهتر است برنامه را یکبار ببندی و دوباره اجرا کنی.",
                )
    # ================= helperها =================
    def _feature_by_index(self, idx: int):
        if 0 <= idx < len(self.features):
            return self.features[idx]
        return None

    def _on_menu_change(self, idx: int):
        feat = self._feature_by_index(idx)
        if feat is None:
            return

        role = self.current_user.get("role", "user")
        if role not in feat.get("roles", ["admin", "user"]):
            QtWidgets.QMessageBox.warning(self, "دسترسی", "شما به این بخش دسترسی ندارید.")
            self._restore_selection()
            return

        self.stack.setCurrentIndex(idx)
        self._last_idx = idx

    def _restore_selection(self):
        self._pw_restore = True
        try:
            self.menu._on(self._last_idx)
        except Exception:
            pass
        try:
            self.stack.setCurrentIndex(self._last_idx)
        except Exception:
            pass

    # ================= اکشن‌ها =================
    def _open_license_dialog(self):
        """
        Ctrl+L → فقط ادمین می‌تواند ماژول‌های فعال برای این شرکت را تغییر دهد.
        """
        if self.current_user.get("role") != "admin":
            QtWidgets.QMessageBox.warning(self, "دسترسی", "فقط ادمین می‌تواند ماژول‌ها را مدیریت کند.")
            return

        dlg = LicenseDialog(self, current_enabled=self.enabled_features, config=self.config)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        new_enabled = sorted(dlg.enabled_ids())
        self.enabled_features = new_enabled
        self.config["enabled_features"] = new_enabled
        save_config(self.config)

        QtWidgets.QMessageBox.information(
            self,
            "ذخیره شد",
            "ماژول‌های فعال برای این شرکت ذخیره شد.\n"
            "برای اعمال کامل تغییرات، برنامه را یک بار ببندید و دوباره اجرا کنید.",
        )

    def _open_users_dialog(self):
    # فقط ادمین اجازه مدیریت کاربران را داشته باشد
        if self.current_user.get("role") != "admin":
            QtWidgets.QMessageBox.warning(self, "دسترسی ممنوع", "فقط ادمین می‌تواند کاربران را مدیریت کند.")
            return

        session = get_session()
        dlg = ManageUsersDialog(self, session=session, enabled_features=self.enabled_features)
        dlg.exec()
    def _build_menus(self):
        menubar = self.menuBar()

        settings_menu = menubar.addMenu("تنظیمات")

        self.action_manage_users = QtWidgets.QAction("مدیریت کاربران", self)
        self.action_manage_users.triggered.connect(self.on_manage_users)

        settings_menu.addAction(self.action_manage_users)

    def on_manage_users(self):
        if self.current_user.get("role") != "admin":
            QtWidgets.QMessageBox.warning(self, "دسترسی ممنوع", "فقط ادمین می‌تواند کاربران را مدیریت کند.")
            return

        session = get_session()
        dlg = ManageUsersDialog(self, session=session, enabled_features=self.enabled_features)
        dlg.exec()