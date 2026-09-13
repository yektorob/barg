# ui/dialogs.py
from typing import List, Dict, Optional

from sqlalchemy.orm import Session

from .qt import QtWidgets, QtCore
from ..core.security import hash_password, verify_password, password_strength_errors
from ..core import licensing
from ..core.db import User
from ..core import users as core_users


# ---------- ساخت ادمین اولیه روی دیتابیس ----------


class InitialAdminDialog(QtWidgets.QDialog):
    """
    وقتی هیچ کاربری تو دیتابیس نیست، این دیالوگ باز می‌شود و
    اولین ادمین را می‌سازد.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ایجاد ادمین اولیه")
        self.setModal(True)
        self.setMinimumWidth(380)

        self._data: Optional[Dict] = None

        self.edit_username = QtWidgets.QLineEdit(self)
        self.edit_username.setPlaceholderText("نام کاربری ادمین (مثلاً admin)")

        self.edit_pass = QtWidgets.QLineEdit(self)
        self.edit_pass.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.edit_pass.setPlaceholderText("رمز ادمین")

        self.edit_confirm = QtWidgets.QLineEdit(self)
        self.edit_confirm.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.edit_confirm.setPlaceholderText("تکرار رمز ادمین")

        btn_ok = QtWidgets.QPushButton("ایجاد", self)
        btn_cancel = QtWidgets.QPushButton("خروج", self)

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        form = QtWidgets.QFormLayout()
        form.addRow("نام کاربری:", self.edit_username)
        form.addRow("رمز ادمین:", self.edit_pass)
        form.addRow("تکرار رمز:", self.edit_confirm)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(form)
        lay.addStretch(1)
        lay.addLayout(btns)

    def get_data(self) -> Optional[Dict]:
        return self._data

    def accept(self):
        username = (self.edit_username.text() or "").strip()
        p1 = (self.edit_pass.text() or "").strip()
        p2 = (self.edit_confirm.text() or "").strip()

        if not username or not p1 or not p2:
            QtWidgets.QMessageBox.warning(self, "خطا", "نام کاربری و هر دو رمز را وارد کنید.")
            return
        if p1 != p2:
            QtWidgets.QMessageBox.warning(self, "خطا", "رمز و تکرار آن یکسان نیست.")
            return

        errors = password_strength_errors(p1)
        if errors:
            QtWidgets.QMessageBox.warning(self, "رمز ضعیف است", "\n".join(errors))
            return

        self._data = {"username": username, "password": p1}
        super().accept()


def ensure_initial_admin_user(session: Session, parent=None):
    """
    اگر هیچ کاربری در دیتابیس وجود نداشته باشد، دیالوگ ایجاد ادمین را باز می‌کند
    و یک یوزر با نقش 'admin' می‌سازد.
    """
    existing = session.query(User).limit(1).all()
    if existing:
        return

    dlg = InitialAdminDialog(parent)
    if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        # بدون ادمین، سیستم معنی ندارد
        raise SystemExit(0)

    data = dlg.get_data()
    if not data:
        raise SystemExit(0)

    u = User(
        username=data["username"],
        password_hash=hash_password(data["password"]),
        role="admin",
        is_active=True,
    )
    session.add(u)
    session.commit()


# ---------- دیالوگ ساخت/ویرایش یک کاربر ----------


class UserEditDialog(QtWidgets.QDialog):
    """
    دیالوگ افزودن/ویرایش کاربر.
    مستقیم با دیتابیس کار نمی‌کند؛ فقط داده‌ی فرم را برمی‌گرداند.
    """
    def __init__(
        self,
        parent=None,
        mode: str = "add",
        user_row: Optional[Dict] = None,
        *,
        licensed_features: Optional[List[str]] = None,
        user_features: Optional[List[str]] = None,
    ):
        super().__init__(parent)
        self.setModal(True)
        self.setMinimumWidth(480)
        self.mode = mode
        self._user_row = user_row or {}

        if mode == "add":
            self.setWindowTitle("افزودن کاربر")
        else:
            self.setWindowTitle("ویرایش کاربر")

        # نقش و نام کاربری
        self.edit_username = QtWidgets.QLineEdit(self)
        self.edit_role = QtWidgets.QComboBox(self)
        self.edit_role.addItems(["admin", "user"])

        # رمز
        self.edit_pass = QtWidgets.QLineEdit(self)
        self.edit_pass.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

        self.edit_confirm = QtWidgets.QLineEdit(self)
        self.edit_confirm.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

        # مقداردهی اولیه
        if user_row:
            self.edit_username.setText(user_row.get("username", ""))
            self.edit_role.setCurrentText(user_row.get("role", "user"))

        if mode == "edit":
            self.edit_username.setEnabled(False)

        # دسترسی ماژول‌ها برای این کاربر
        # فقط ماژول‌هایی که شرکت لایسنس‌شان را دارد
        all_feats = licensing.ALL_FEATURES
        if licensed_features is None:
            licensed_ids = {f["id"] for f in all_feats}
        else:
            licensed_ids = set(licensed_features)

        user_feats_set = set(user_features or [])
        self._feature_checks: Dict[str, QtWidgets.QCheckBox] = {}
        self._licensed_feature_ids = licensed_ids

        # فرم اصلی
        form = QtWidgets.QFormLayout()
        form.addRow("نام کاربری:", self.edit_username)
        form.addRow("نقش:", self.edit_role)
        form.addRow("رمز عبور:", self.edit_pass)
        form.addRow("تکرار رمز:", self.edit_confirm)

        # گروه ماژول‌ها
        group_box = QtWidgets.QGroupBox("دسترسی به ماژول‌ها", self)
        vbox_feats = QtWidgets.QVBoxLayout(group_box)

        for feat in all_feats:
            fid = feat["id"]
            if fid not in licensed_ids:
                continue
            cb = QtWidgets.QCheckBox(feat["title"], group_box)
            # اگر برای این کاربر چیزی ذخیره نشده، پیش‌فرض: همه‌ی ماژول‌های لایسنس‌شده فعال
            if user_feats_set:
                cb.setChecked(fid in user_feats_set)
            else:
                cb.setChecked(True)
            self._feature_checks[fid] = cb
            vbox_feats.addWidget(cb)

        vbox_feats.addStretch(1)

        btn_ok = QtWidgets.QPushButton("ذخیره", self)
        btn_cancel = QtWidgets.QPushButton("انصراف", self)

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(group_box)
        lay.addStretch(1)
        lay.addLayout(btns)

    def _collect_selected_features(self, role: str) -> List[str]:
        """
        لیست ماژول‌هایی که تیک خورده و با نقش کاربر همخوانی دارند.
        """
        selected: List[str] = []
        feats_by_id = {f["id"]: f for f in licensing.ALL_FEATURES}

        for fid, cb in self._feature_checks.items():
            if not cb.isChecked():
                continue
            feat = feats_by_id.get(fid)
            if not feat:
                continue
            # فقط ماژول‌هایی که برای این نقش اجازه دارند
            if role not in feat.get("roles", ["user"]):
                continue
            selected.append(fid)

        # یکتا و مرتب
        return sorted(set(selected))

    def get_data(self) -> Optional[Dict]:
        username = (self.edit_username.text() or "").strip()
        role = (self.edit_role.currentText() or "").strip()
        p1 = (self.edit_pass.text() or "").strip()
        p2 = (self.edit_confirm.text() or "").strip()

        if not username:
            QtWidgets.QMessageBox.warning(self, "خطا", "نام کاربری نمی‌تواند خالی باشد.")
            return None
        if role not in ("admin", "user"):
            role = "user"

        if self.mode == "add" or p1 or p2:
            if p1 != p2:
                QtWidgets.QMessageBox.warning(self, "خطا", "دو رمز وارد شده یکسان نیستند.")
                return None
            errors = password_strength_errors(p1)
            if errors:
                QtWidgets.QMessageBox.warning(self, "رمز ضعیف است", "\n".join(errors))
                return None

        features = self._collect_selected_features(role)

        return {
            "id": self._user_row.get("id"),
            "username": username,
            "role": role,
            "password": p1,
            "features": features,
        }


# ---------- پنل مدیریت کاربران (روی دیتابیس) ----------


class ManageUsersDialog(QtWidgets.QDialog):
    """
    دیالوگ مدیریت کاربران:
    - افزودن
    - ویرایش نقش/رمز
    - تنظیم دسترسی ماژول‌ها
    - حذف (با اجبار حداقل یک ادمین)
    همه چیز روی جدول users در دیتابیس ذخیره می‌شود.
    """
    def __init__(
        self,
        parent=None,
        session: Optional[Session] = None,
        *,
        enabled_features: Optional[List[str]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("مدیریت کاربران")
        self.setModal(True)
        self.setMinimumWidth(480)

        if session is None:
            raise RuntimeError("ManageUsersDialog نیاز به Session دیتابیس دارد.")
        self._session: Session = session

        # ماژول‌هایی که این نصب طبق لایسنس می‌تواند استفاده کند
        self._enabled_feature_ids = set(enabled_features or [])

        layout = QtWidgets.QVBoxLayout(self)

        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "نام کاربری", "نقش"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        btn_add = QtWidgets.QPushButton("افزودن کاربر")
        btn_edit = QtWidgets.QPushButton("ویرایش کاربر")
        btn_del = QtWidgets.QPushButton("حذف کاربر")
        btn_close = QtWidgets.QPushButton("بستن")

        btn_add.clicked.connect(self._on_add)
        btn_edit.clicked.connect(self._on_edit)
        btn_del.clicked.connect(self._on_delete)
        btn_close.clicked.connect(self.accept)

        row_btns = QtWidgets.QHBoxLayout()
        row_btns.addWidget(btn_add)
        row_btns.addWidget(btn_edit)
        row_btns.addWidget(btn_del)
        row_btns.addStretch(1)
        row_btns.addWidget(btn_close)
        layout.addLayout(row_btns)

        self._reload_table()

    def _reload_table(self):
        users = self._session.query(User).order_by(User.username).all()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "نام کاربری", "نقش", "ماژول‌ها"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setRowCount(len(users))

        # mapping id -> title for display
        feat_title_by_id = {f["id"]: f["title"] for f in licensing.ALL_FEATURES}

        for row, u in enumerate(users):
            it_id = QtWidgets.QTableWidgetItem(str(u.id))
            it_user = QtWidgets.QTableWidgetItem(u.username)
            it_role = QtWidgets.QTableWidgetItem(u.role or "user")

            # parse stored feature_perms and display titles (comma-separated)
            from ..core import users as core_users

            fids = core_users.parse_feature_ids(getattr(u, "feature_perms", None))
            titles = [feat_title_by_id.get(fid, fid) for fid in fids]
            feats_text = ", ".join(titles) if titles else "—"

            # use a QLabel with word-wrap inside the cell so long lists are fully visible
            lbl = QtWidgets.QLabel(feats_text)
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

            self.table.setItem(row, 0, it_id)
            self.table.setItem(row, 1, it_user)
            self.table.setItem(row, 2, it_role)
            self.table.setCellWidget(row, 3, lbl)

        # adjust sizing so wrapped contents are visible
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

    def _selected_user_id(self) -> Optional[int]:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        item = self.table.item(row, 0)
        if not item:
            return None
        try:
            return int(item.text())
        except (TypeError, ValueError):
            return None

    def _on_add(self):
        dlg = UserEditDialog(
            self,
            mode="add",
            user_row=None,
            licensed_features=list(self._enabled_feature_ids),
            user_features=None,
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data:
            return

        exists = self._session.query(User).filter(User.username == data["username"]).first()
        if exists:
            QtWidgets.QMessageBox.warning(self, "خطا", "کاربری با این نام قبلاً وجود دارد.")
            return

        if not data["password"]:
            QtWidgets.QMessageBox.warning(self, "خطا", "برای کاربر جدید باید رمز تعریف کنید.")
            return

        feature_str = core_users.serialize_feature_ids(data.get("features") or [])

        u = User(
            username=data["username"],
            role=data["role"],
            password_hash=hash_password(data["password"]),
            is_active=True,
            feature_perms=feature_str,
        )
        self._session.add(u)
        self._session.commit()
        self._reload_table()

    def _on_edit(self):
        user_id = self._selected_user_id()
        if user_id is None:
            QtWidgets.QMessageBox.warning(self, "خطا", "لطفاً یک کاربر را انتخاب کنید.")
            return

        u = self._session.get(User, user_id)
        if not u:
            QtWidgets.QMessageBox.warning(self, "خطا", "کاربر یافت نشد.")
            return

        current_features = core_users.parse_feature_ids(getattr(u, "feature_perms", None))

        dlg = UserEditDialog(
            self,
            mode="edit",
            user_row={"id": u.id, "username": u.username, "role": u.role},
            licensed_features=list(self._enabled_feature_ids),
            user_features=current_features,
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data:
            return

        u.role = data["role"]
        if data["password"]:
            u.password_hash = hash_password(data["password"])
        u.feature_perms = core_users.serialize_feature_ids(data.get("features") or [])
        self._session.commit()
        self._reload_table()

    def _on_delete(self):
        user_id = self._selected_user_id()
        if user_id is None:
            QtWidgets.QMessageBox.warning(self, "خطا", "لطفاً یک کاربر را انتخاب کنید.")
            return

        u = self._session.get(User, user_id)
        if not u:
            QtWidgets.QMessageBox.warning(self, "خطا", "کاربر یافت نشد.")
            return

        if u.role == "admin":
            admins = (
                self._session.query(User)
                .filter(User.role == "admin", User.id != u.id)
                .all()
            )
            if not admins:
                QtWidgets.QMessageBox.warning(
                    self, "خطا", "حداقل یک کاربر با نقش ادمین لازم است."
                )
                return

        if QtWidgets.QMessageBox.question(
            self, "حذف", "این کاربر حذف شود؟"
        ) != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        self._session.delete(u)
        self._session.commit()
        self._reload_table()


# ---------- دیالوگ لایسنس ----------


class LicenseDialog(QtWidgets.QDialog):
    """
    فقط برای ادمین – تعیین می‌کند این شرکت چه ماژول‌هایی خریده.

    این دیالوگ دو راه پیش می‌گذارد:
      - آپلود فایل لایسنس (ترجیح داده می‌شود) — فایل بررسی و در صورت معتبر
        با `licensing.apply_license` روی `config` اعمال می‌شود.
      - یا انتخاب دستی ماژول‌ها با چک‌باکس‌ها (فقط زمانی که فایل آپلود نشده).
    """
    def __init__(self, parent=None, current_enabled=None, config: Optional[Dict] = None):
        super().__init__(parent)
        self.setWindowTitle("مدیریت ماژول‌ها / لایسنس")
        self.setModal(True)
        self.setMinimumWidth(480)

        if current_enabled is None:
            current_enabled = []

        self._checks: Dict[str, QtWidgets.QCheckBox] = {}
        self._uploaded_license_path: Optional[str] = None
        self._uploaded_license_features: Optional[List[str]] = None
        self._config = config
        self._result: Optional[Dict] = None

        layout = QtWidgets.QVBoxLayout(self)
        info = QtWidgets.QLabel(
            "برای فعال‌سازی ماژول‌ها یک فایل لایسنس معتبر (JSON) آپلود کنید:")
        info.setWordWrap(True)
        layout.addWidget(info)

        # ----- آپلود فایل لایسنس -----
        row = QtWidgets.QHBoxLayout()
        self.edit_license_path = QtWidgets.QLineEdit(self)
        btn_browse = QtWidgets.QPushButton("انتخاب فایل...", self)
        btn_browse.clicked.connect(self._on_browse_license)
        row.addWidget(self.edit_license_path, 1)
        row.addWidget(btn_browse)
        layout.addLayout(row)

        self.lbl_license_preview = QtWidgets.QLabel("")
        self.lbl_license_preview.setWordWrap(True)
        layout.addWidget(self.lbl_license_preview)

        # دکمه اعمال فایل (در صورت آپلود)
        self.btn_apply_file = QtWidgets.QPushButton("اعمال فایل لایسنس", self)
        self.btn_apply_file.clicked.connect(self._on_apply_file)
        self.btn_apply_file.setEnabled(False)
        layout.addWidget(self.btn_apply_file)

        layout.addStretch(1)

        btn_ok = QtWidgets.QPushButton("بستن", self)
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok)

    def _on_browse_license(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "انتخاب فایل لایسنس", "", "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        self.edit_license_path.setText(path)
        try:
            lic = licensing.load_and_verify_license_from_file(path)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "فایل نامعتبر", f"فایل لایسنس نامعتبر است:\n{e}")
            self._uploaded_license_path = None
            self._uploaded_license_features = None
            self.lbl_license_preview.setText("")
            self.btn_apply_file.setEnabled(False)
            return

        feats = licensing.features_from_license_dict(lic)
        self._uploaded_license_path = path
        self._uploaded_license_features = feats
        preview = f"شرکت: {lic.get('company','')}, انقضا: {lic.get('expires','')}\nماژول‌ها: {', '.join(feats) or '—'}"
        self.lbl_license_preview.setText(preview)
        self.btn_apply_file.setEnabled(True)

    def _on_apply_file(self):
        if not self._uploaded_license_path:
            return
        if self._config is None:
            # پیش‌نمایش — برگرداندن نتیجه بدون نوشتن روی config
            self._result = {"enabled_ids": list(self._uploaded_license_features or [])}
            QtWidgets.QMessageBox.information(self, "پیش‌نمایش", "فایل لایسنس معتبر است. (config ارائه نشده، ذخیره انجام نشد)")
            return
        try:
            enabled = licensing.apply_license(self._config, license_path=self._uploaded_license_path)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "خطا", f"اعمال لایسنس ناموفق بود:\n{e}")
            return
        self._result = {"enabled_ids": enabled}
        QtWidgets.QMessageBox.information(self, "ذخیره شد", "فایل لایسنس اعمال و ذخیره شد.")

    def get_result(self) -> Optional[Dict]:
        return self._result

    def accept(self):
        # Require that a license file was uploaded (and applied if config provided)
        if not self._uploaded_license_path:
            QtWidgets.QMessageBox.warning(self, "نیاز به فایل لایسنس", "لطفاً یک فایل لایسنس معتبر آپلود و اعمال کنید.")
            return

        if self._config is not None and not self._result:
            # try to apply automatically
            self._on_apply_file()
            if not self._result:
                return

        # if config is None, _result may be set by _on_browse_license (preview) or by _on_apply_file
        if not self._result:
            # create a preview result from uploaded features
            self._result = {"enabled_ids": list(self._uploaded_license_features or [])}

        super().accept()


# ---------- لاگین ----------


class LoginDialog(QtWidgets.QDialog):
    """
    دیالوگ لاگین: نام کاربری + رمز (از دیتابیس)
    """
    def __init__(self, parent=None, session: Optional[Session] = None):
        super().__init__(parent)
        self.setWindowTitle("ورود به سیستم")
        self.setModal(True)
        self.setMinimumWidth(360)

        if session is None:
            raise RuntimeError("LoginDialog نیاز به Session دیتابیس دارد.")
        self._session: Session = session
        self._user: Optional[Dict] = None

        self.edit_user = QtWidgets.QLineEdit(self)
        self.edit_user.setPlaceholderText("نام کاربری")

        self.edit_pass = QtWidgets.QLineEdit(self)
        self.edit_pass.setPlaceholderText("رمز عبور")
        self.edit_pass.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

        btn_ok = QtWidgets.QPushButton("ورود", self)
        btn_cancel = QtWidgets.QPushButton("خروج", self)

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        form = QtWidgets.QFormLayout()
        form.addRow("نام کاربری:", self.edit_user)
        form.addRow("رمز عبور:", self.edit_pass)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(form)
        lay.addStretch(1)
        lay.addLayout(btns)

    def get_user(self) -> Optional[Dict]:
        return self._user

    def accept(self):
        username = (self.edit_user.text() or "").strip()
        password = (self.edit_pass.text() or "").strip()
        if not username or not password:
            QtWidgets.QMessageBox.warning(self, "خطا", "نام کاربری و رمز عبور را وارد کنید.")
            return

        u: Optional[User] = (
            self._session.query(User)
            .filter(User.username == username, User.is_active == True)  # noqa: E712
            .first()
        )
        if not u:
            QtWidgets.QMessageBox.warning(self, "خطا", "کاربر یافت نشد یا غیرفعال است.")
            return

        if not verify_password(password, u.password_hash):
            QtWidgets.QMessageBox.warning(self, "خطا", "رمز عبور نادرست است.")
            return

        role = u.role or "user"
        if role not in ("admin", "user"):
            role = "user"

        feature_ids = core_users.parse_feature_ids(getattr(u, "feature_perms", None))

        self._user = {
            "id": u.id,
            "username": u.username,
            "role": role,
            "features": feature_ids,
        }
        super().accept()


def login_and_get_user(session: Session, parent=None) -> Optional[Dict]:
    """
    دیالوگ لاگین را تا زمانی که کاربر درست وارد کند یا Cancel بزند، تکرار می‌کند.
    """
    while True:
        dlg = LoginDialog(parent, session=session)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return None
        u = dlg.get_user()
        if u:
            return u