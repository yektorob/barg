# === Boot patch: ensure UI & helpers are importable in EXE/Data layout ===
try:
    import os, sys
    BASE = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(sys.argv[0])))
    UI_DIR = os.path.join(BASE, "ui")
    # Make 'ui' package or plain modules discoverable
    if UI_DIR not in sys.path:
        sys.path.insert(0, UI_DIR)
    if BASE not in sys.path:
        sys.path.insert(0, BASE)
    # Ensure child subprocesses see helpers when running editor_window/edit_window directly
    _prev_pp = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = (BASE + os.pathsep + _prev_pp) if _prev_pp else BASE
except Exception:
    pass
# === End boot patch ===
# ui/app3_widget.py
# -*- coding: utf-8 -*-

import os
import json
import sys, re, json, shutil, uuid, urllib.parse, urllib.request, subprocess, sys
import datetime
from typing import Any, Dict, List, Tuple

import jdatetime

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QSize, QUrl, QMarginsF
from PySide6.QtGui import (
    QDesktopServices, QIcon
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QDialog, QFormLayout, QTextEdit, QLineEdit, QFileDialog, QMessageBox,
    QStyle, QSizePolicy, QGridLayout, QComboBox, QToolButton, QTableWidget, QTableWidgetItem, QHeaderView
)

from tax_logic import load_files, save_file, delete_file
from core.tax_db import TaxFileDB

# ================ مسیرها و تنظیمات سراسری ================
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR) if os.path.basename(_THIS_DIR) in ("tax_apps","ui","app","apps") else _THIS_DIR
UPLOAD_ROOT = r"D:\uploads"
os.makedirs(UPLOAD_ROOT, exist_ok=True)
# استایل سفارشی (اختیاری)
ABBASPOOR_QSS = os.path.join(_PROJECT_ROOT, "styles", "abbaspoor.qss")


# ================ برچسب‌های فارسی ================
PERSIAN_LABELS = {
    "company_name": "نام شرکت",
    "fiscal_year": "سال مالی",
    "entry_date": "تاریخ ورود به موسسه",
    "case_type": "نوع پرونده",
    "last_action_date": "تاریخ آخرین اقدام",
    "current_stage": "مرحله فعلی",
    "notes": "یادداشت",
    "reminder notes": "یادداشت یادآوری",
    "reminder_notes": "یادداشت یادآوری",
    "uploaded_files": "فایل‌های آپلودی",
    "petition_uploaded_files": "فایل‌های آپلودی دادخواست",
    "submit_date": "تاریخ ارائه اسناد و مدارک",
    "deadline_days": "مهلت (روز)",
    "due_date": "مهلت ارائه اسناد و مدارک",
    "submit_status": "وضعیت ارائه اسناد",
    "upload_date": "تاریخ ارائه مدارک",
    "has_assessment": "برگه تشخیص دارد؟",
    "assessment_date": "تاریخ صدور برگه تشخیص",
    "assessment_deadline": "مهلت اعتراض برگه تشخیص",
    "report_exists": "گزارش رسیدگی دارد؟",
    "objected": "اعتراض شده؟",
    "appeal_send_date": "تاریخ اعتراض",
    "mad238_entry_date": "تاریخ ورود ماده ۲۳۸",
    "mad238_agreement_deadline": "مهلت توافق ماده ۲۳۸",
    "jarime_amount": "مبلغ جریمه (تومان)",
    "bodavi_session_date": "جلسه بدوی",
    "bodavi_verdict_date": "تاریخ رأی بدوی",
    "bodavi_appeal_deadline": "مهلت اعتراض بدوی",
    "bodavi_appeal_done": "اعتراض به رأی بدوی انجام شد؟",
    "bodavi_appeal_date": "تاریخ اعتراض به رأی بدوی",
    "bodavi_verdict": "نتیجه رأی بدوی",
    "needs_investigation": "نیاز به تحقیق/کارشناسی",
    "tajdid_refer_date": "ارجاع به هیأت تجدیدنظر",
    "needs_investigation_tajdid": "نیاز به تحقیق/کارشناسی (تجدیدنظر)",
    "tajdid_expert_date": "تاریخ کارشناسی (تجدیدنظر)",
    "verdict_date_tajdid": "تاریخ رأی تجدیدنظر",
    "objection_deadline_tajdid": "مهلت اعتراض (تجدیدنظر)",
    "objection_done_tajdid": "اعتراض انجام شد؟ (تجدیدنظر)",
    "objection_date_tajdid": "تاریخ اعتراض (تجدیدنظر)",
    "verdict_result_tajdid": "نتیجه رأی تجدیدنظر",
    "verification_status": "احراز دبیرخانه شورا",
    "council_date": "تاریخ شورا",
    "final_amount": "مبلغ نهایی",
    "status": "وضعیت",
}
def fa_label(key: str) -> str:
    return PERSIAN_LABELS.get(key, key)

# ================ Utils ================
def _format_value(v: Any) -> str:
    if v is None or v == "": return "—"
    if isinstance(v, (list, dict)):
        try: return json.dumps(v, ensure_ascii=False)
        except Exception: return str(v)
    return str(v)

def _basename_only(name_or_path: str) -> str:
    s = str(name_or_path or "").strip().strip('<>').strip('"').strip("'")
    try:
        p = urllib.parse.urlparse(s)
        if p.scheme in ("http","https","ftp","file"):
            base = os.path.basename(p.path)
            return base or "file"
    except Exception:
        pass
    s2 = s.replace("/", "\\")
    base = os.path.basename(s2)
    if base and base != s: return base
    if "/" in s or "\\" in s: return s.split("/")[-1].split("\\")[-1] or "file"
    return s or "file"

def _normalize_files_list(val) -> List[Tuple[str,str]]:
    def clean_str(s: str) -> str:
        s = str(s).strip().strip('<>').strip('"').strip("'")
        hp, fp = s.find("http"), s.find("file://")
        if hp > 0: s = s[hp:]
        elif fp > 0: s = s[fp:]
        return s.strip()
    def is_win(p: str) -> bool:
        return bool(re.match(r'^[A-Za-z]:[\\/]', p)) or p.startswith('\\\\')
    def to_pair(x):
        if isinstance(x, dict):
            raw = x.get("url") or x.get("link") or x.get("path") or ""
            raw = clean_str(raw)
            if not raw: return None
            name = x.get("name") or x.get("filename") or ""
            name = _basename_only(name) if name else _basename_only(raw)
            return (name, raw)
        s = clean_str(x)
        if not s: return None
        if re.match(r'^(https?|ftp)://', s, re.IGNORECASE): return (_basename_only(s), s)
        if s.lower().startswith("file://"): return (_basename_only(s), s)
        if is_win(s.replace("/", "\\")):   return (_basename_only(s), s)
        if re.match(r'^[A-Za-z0-9][A-Za-z0-9\.\-]+\.[A-Za-z]{2,}(/.*)?$', s):
            s2 = "https://" + s; return (_basename_only(s2), s2)
        return (_basename_only(s), s)
    out = []
    if isinstance(val, list):
        for it in val:
            p = to_pair(it)
            if p: out.append(p)
    elif isinstance(val, str):
        for p in re.split(r"[,\n;]+", val):
            par = to_pair(p.strip())
            if par: out.append(par)
    elif val is not None:
        p = to_pair(val)
        if p: out.append(p)
    seen, uniq = set(), []
    for n, u in out:
        if u in seen: continue
        seen.add(u); uniq.append((n,u))
    return uniq

def _load_icon_like_bell():
    candidates = [
        os.path.join(_PROJECT_ROOT, "icons", "bell.png"),
        os.path.join(_PROJECT_ROOT, "assets", "icons", "bell.png"),
        os.path.join(_THIS_DIR, "icons", "bell.png"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return QIcon(p)
    ic = QtWidgets.QApplication.style().standardIcon(QStyle.SP_MessageBoxInformation)
    return ic

def _ensure_qapp():
    """اگر QApplication وجود نداشت، یک نمونهٔ موقتی بساز (برای مسیرهای مستقل)."""
    app = QApplication.instance()
    if app is None:
        return QApplication(sys.argv)
    return app

# [PDF export removed]
# ---------- منطق خالص جستجو ----------
def search_records(records: List[Dict], query: str,
                   mode: str = "contains",
                   fields: Tuple[str, ...] = ("company_name",)) -> List[Tuple[int, Dict]]:
    q = (query or "").strip().lower()
    if not q:
        return []
    def norm(x):
        return str(x or "").strip().lower()
    out: List[Tuple[int, Dict]] = []
    for i, r in enumerate(records):
        hay = [norm(r.get(f, "")) for f in fields]
        if mode == "contains":
            if any(q in h for h in hay):
                out.append((i, r))
        else:  # exact
            if any(q == h for h in hay):
                out.append((i, r))
    return out

# ================ ویجت کارت ================
class CompanyCardWidget(QFrame):
    clickedDetails = QtCore.Signal()
    def __init__(self, company: str, fiscal_year: str, entry_date: str, last_action_date: str, case_type: str, status: str, parent=None):
        # اضافه‌شده: وضعیت برای نمایش روی کارت

        super().__init__(parent)
        self.setObjectName("CardFrame")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(120)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet("""
        #CardFrame {border:1px solid rgba(255,255,255,0.10); border-radius:8px;}
        #CardFrame QLabel[cardTitle="true"] {font-weight:600;}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)

        right = QVBoxLayout()
        right.setSpacing(6)
        right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl1 = QLabel(f"{fa_label('company_name')}: {company}"); lbl1.setProperty("cardTitle", True)
        lbl2 = QLabel(f"{fa_label('fiscal_year')}: {fiscal_year}")
        lbl3 = QLabel(f"{fa_label('entry_date')}: {entry_date}")
        lbl4 = QLabel(f"{fa_label('last_action_date')}: {last_action_date}")
        lbl5 = QLabel(f"{fa_label('case_type')}: {case_type}")
        lbl6 = QLabel(f"{fa_label('status')}: {status}")
        for w in (lbl1, lbl2, lbl3, lbl4, lbl5, lbl6):
            w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            w.setWordWrap(True)
            w.setTextInteractionFlags(Qt.TextSelectableByMouse)
            w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        right.addWidget(lbl1); right.addWidget(lbl2); right.addWidget(lbl3); right.addWidget(lbl4); right.addWidget(lbl5); right.addWidget(lbl6)

        btn = QPushButton("مشاهده جزئیات")
        btn.setObjectName("CardActionBtn")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.clickedDetails.emit)

        lay.addLayout(right, 1)
        lay.addWidget(btn, 0, Qt.AlignLeft | Qt.AlignVCenter)

# ================ دیالوگ تنظیمات یادآوری (بدون انصراف) ================
class ReminderSettingsDialog(QDialog):
    def __init__(self, rec: dict, save_callback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تنظیمات یادآوری")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet("""
        #CardFrame {border:1px solid rgba(255,255,255,0.10); border-radius:8px;}
        #CardFrame QLabel[cardTitle="true"] {font-weight:600;}
        """)
        self.rec = rec
        self._save_callback = save_callback
        self.setMinimumWidth(360)

        form = QFormLayout(self)
        form.setLabelAlignment(Qt.AlignRight)

        self.days = QtWidgets.QSpinBox()
        self.days.setRange(0, 365)
        self.days.setSingleStep(1)
        self.days.setValue(int(rec.get("notify_days") or 0))

        self.mode = QComboBox()
        self.mode.addItem("—", None)
        self.mode.addItem("یک بار",  "once")
        self.mode.addItem("دوبار",   "twice")
        self.mode.addItem("روزانه",  "daily")
        cur = (rec.get("notify_mode") or "").strip().lower()
        idx = self.mode.findData(cur if cur in ("once","twice","daily") else None)
        self.mode.setCurrentIndex(idx if idx >= 0 else 0)

        form.addRow("چند روز قبل:", self.days)
        form.addRow("حالت:", self.mode)

        # فقط «ذخیره»
        row = QHBoxLayout()
        self.ok = QPushButton("ذخیره")
        self.ok.setEnabled(False)
        self.ok.clicked.connect(self.on_save)
        row.addStretch(1); row.addWidget(self.ok, 0, Qt.AlignLeft)
        form.addRow(row)

        self._orig_days = int(self.days.value())
        self._orig_mode = self.mode.currentData()
        self.days.valueChanged.connect(self._on_changed)
        self.mode.currentIndexChanged.connect(self._on_changed)

        self.setStyleSheet("""
        QSpinBox {
            background:#2C2E33; color:#F5F5F5;
            border:1px solid #383838; border-radius:8px; padding-right:28px; height:32px;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            width:24px; border:none; background:transparent; margin:0;
        }
        QSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; }
        QSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; }
        QSpinBox::up-arrow, QSpinBox::down-arrow { width:10px; height:10px; }

        QComboBox {
            background:#2C2E33; color:#F5F5F5;
            border:1px solid #383838; border-radius:8px; padding:4px 28px 4px 8px; min-height:32px;
        }
        QComboBox::drop-down { width:24px; border:none; }
        QComboBox QAbstractItemView { background:#1F2125; color:#F5F5F5; selection-background-color:#3A3D44; }
        """)

    def _on_changed(self, *a):
        changed = (int(self.days.value()) != self._orig_days) or (self.mode.currentData() != self._orig_mode)
        self.ok.setEnabled(changed)

    def on_save(self):
        # مقادیر قبلی
        old_days = int(self.rec.get("notify_days", 0) or 0)
        old_mode = self.rec.get("notify_mode", None)

        # مقادیر جدید
        d = int(self.days.value())
        sel = self.mode.currentData()

        changed = False

        # به‌روزرسانی notify_days
        if d == 0:
            if "notify_days" in self.rec and old_days != 0:
                changed = True
            self.rec.pop("notify_days", None)
        else:
            if old_days != d:
                changed = True
            self.rec["notify_days"] = d

        # به‌روزرسانی notify_mode
        if sel is None:
            if "notify_mode" in self.rec and old_mode is not None:
                changed = True
            self.rec.pop("notify_mode", None)
        else:
            if old_mode != sel:
                changed = True
            self.rec["notify_mode"] = sel

        if changed and callable(self._save_callback):
            self._save_callback(self.rec)
        self.accept()

# ================ دیالوگ ویرایش یادداشت (همان قبلی) ================
class NoteEditDialog(QDialog):
    def __init__(self, title: str, initial_text: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet("""
        #CardFrame {border:1px solid rgba(255,255,255,0.10); border-radius:8px;}
        #CardFrame QLabel[cardTitle="true"] {font-weight:600;}
        """)
        v = QVBoxLayout(self)
        self.text = QTextEdit(); self.text.setPlainText(initial_text or "")
        v.addWidget(self.text)
        row = QHBoxLayout()
        ok = QPushButton("ذخیره"); cancel = QPushButton("انصراف")
        ok.clicked.connect(self.accept); cancel.clicked.connect(self.reject)
        row.addWidget(ok); row.addWidget(cancel)
        v.addLayout(row)

    def get_text(self) -> str:
        return self.text.toPlainText().strip()

# ================ دیالوگ افزودن URL (همان قبلی) ================
# ================ دیالوگ تعیین تاریخ یادآوری بعدی ================

# ================ دیالوگ تعیین تاریخ یادآوری بعدی ================

# ================ دیالوگ تعیین تاریخ یادآوری بعدی ================
class NextReminderDialog(QDialog):
    def __init__(self, initial_value: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("تاریخ یادآوری بعدی")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(420)

        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.input = QLineEdit()
        self._mask = "0000/00/00; "
        if initial_value:
            self.input.setInputMask(self._mask)
            self.input.setText(str(initial_value).replace("-", "/"))
        else:
            self.input.setInputMask("")
            self.input.setPlaceholderText("")
            self.input.clear()
        self.input.installEventFilter(self)
        form.addRow("تاریخ:", self.input)
        lay.addLayout(form)

        row = QHBoxLayout()
        row.addStretch(1)
        self.btn_ok = QPushButton("ذخیره")
        self.btn_ok.setEnabled(False)
        btn_cancel = QPushButton("انصراف")
        row.addWidget(self.btn_ok)
        row.addWidget(btn_cancel)
        lay.addLayout(row)

        self._initial_norm = self._normalize(initial_value)
        self.input.textChanged.connect(self._on_text_changed)
        self.btn_ok.clicked.connect(self._on_ok)
        btn_cancel.clicked.connect(self.reject)

    def eventFilter(self, obj, ev):
        if obj is self.input:
            et = ev.type()
            if et == QtCore.QEvent.FocusIn:
                if self.input.inputMask() != self._mask:
                    self.input.setInputMask(self._mask)
            elif et == QtCore.QEvent.FocusOut:
                if self._normalize(self.input.text()) == "":
                    self.input.setInputMask("")
                    self.input.setText("")
                    self.btn_ok.setEnabled(False)
        return super().eventFilter(obj, ev)

    def _normalize(self, s: str) -> str:
        import re as _re
        ds = _re.sub(r'\D', '', s or '')
        if not ds:
            return ""
        if len(ds) >= 8:
            return f"{ds[0:4]}/{ds[4:6]}/{ds[6:8]}"
        return ds

    def _normalize_digits(self, s: str) -> str:
        _PERSIAN = "۰۱۲۳۴۵۶۷۸۹"
        _ARABIC  = "٠١٢٣٤٥٦٧٨٩"
        _ASCII   = "0123456789"
        tbl = {**{ord(p): ord(a) for p, a in zip(_PERSIAN, _ASCII)},
               **{ord(a): ord(b) for a, b in zip(_ARABIC,  _ASCII)}}
        return (s or "").translate(tbl)

    def _validate_jalali(self, s: str, fmt: str = "%Y/%m/%d"):
        """بررسی تاریخ شمسی با jdatetime. خروجی: (bool, jdatetime.date|None)"""
        import re as _re
        ss = self._normalize_digits((s or "").strip())
        ss = _re.sub(r"[-.]", "/", ss)
        try:
            dt = jdatetime.datetime.strptime(ss, fmt)
            return True, dt.date()
        except Exception:
            return False, None
    def _is_leap(self, y: int) -> bool:
        return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)

    def _is_valid_date(self, s: str) -> bool:
        ok, _ = self._validate_jalali(s)
        return ok
    def _on_text_changed(self):
        cur = self._normalize(self.input.text())
        ok, _ = self._validate_jalali(cur)
        self.btn_ok.setEnabled(ok and cur != self._initial_norm)
    def _on_ok(self):
        cur = self._normalize(self.input.text())
        ok, jdate = self._validate_jalali(cur)
        if not ok:
            QMessageBox.warning(self, "تاریخ نامعتبر", "رشتهٔ واردشده تاریخ شمسی معتبر نیست. مثال: 1403/07/01")
            self.input.setFocus()
            self.input.selectAll()
            return
        today = jdatetime.date.today()
        if jdate < today:
            QMessageBox.warning(self, "تاریخ گذشته", "تاریخ یادآوری نباید قبل از امروز باشد.")
            self.input.setFocus()
            self.input.selectAll()
            return
        # همه‌چیز درست:
        self.btn_ok.setEnabled(True)
        self.accept()
    def get_value(self) -> str:
        return self._normalize(self.input.text())

class UrlAddDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("افزودن URL")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet("""
        #CardFrame {border:1px solid rgba(255,255,255,0.10); border-radius:8px;}
        #CardFrame QLabel[cardTitle="true"] {font-weight:600;}
        """)
        form = QFormLayout(self)
        self.url = QtWidgets.QLineEdit()
        form.addRow("URL:", self.url)
        row = QHBoxLayout()
        ok = QPushButton("افزودن"); cancel = QPushButton("انصراف")
        ok.clicked.connect(self.accept); cancel.clicked.connect(self.reject)
        row.addWidget(ok); row.addWidget(cancel)
        form.addRow(row)

    def get_url(self) -> str:
        return self.url.text().strip()

# ================ دیالوگ جزئیات (بدون دکمه بستن؛ با ویرایش + PDF) ================
class DetailsDialog(QDialog):
    def __init__(self, parent, rec_index: int, records: List[dict], save_fn, sync_fn, delete_fn, header_order: list | None = None):
        super().__init__(parent)
        self.setWindowTitle("جزئیات پرونده")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet("""
        #CardFrame {border:1px solid rgba(255,255,255,0.10); border-radius:8px;}
        #CardFrame QLabel[cardTitle="true"] {font-weight:600;}
        """)
        self.setMinimumSize(860, 560)
        self.setMaximumSize(1100, 820)
        self.rec_index = rec_index
        self.records = records
        self._save_fn = save_fn
        self._sync_fn = sync_fn
        self._delete_fn = delete_fn
        self.header_order = header_order or []

        self.rec = self.records[self.rec_index]
        company = self.rec.get("company_name", "—")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # هدر
        hdr = QHBoxLayout()
        title = QLabel(f"جزئیات پرونده: {company}")
        title.setProperty("cardTitle", True)
        hdr.addWidget(title, 0, Qt.AlignRight)
        hdr.addStretch(1)

        self.btn_rem = QPushButton()
        self.btn_rem.setText("تنظیمات یادآوری")
        self.btn_rem.clicked.connect(self._open_reminder_dialog)
        self.btn_next_rem = QPushButton()
        self.btn_next_rem.setText("تاریخ یادآوری بعدی")
        self.btn_next_rem.clicked.connect(self._open_next_reminder_dialog)


        # دکمه‌های سمت چپ: ویرایش + حذف
        btn_edit = QPushButton("ویرایش پرونده")
        btn_edit.clicked.connect(self._open_editor)
        btn_del = QPushButton("حذف پرونده")
        hdr.addWidget(self.btn_next_rem, 0, Qt.AlignRight)
        btn_del.setStyleSheet("color:#b00020;")
        btn_del.clicked.connect(self._on_delete)

        hdr.addWidget(self.btn_rem, 0, Qt.AlignRight)
        hdr.addWidget(btn_edit, 0, Qt.AlignLeft)
        hdr.addWidget(btn_del, 0, Qt.AlignLeft)
        root.addLayout(hdr)

        # ScrollArea
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(520)
        wrap = QWidget()
        vwrap = QVBoxLayout(wrap); vwrap.setContentsMargins(0,0,0,0); vwrap.setSpacing(10)

        # یادداشت‌ها (RTL & راست‌چین)
        notes_box = QGroupBoxEx("یادداشت‌ها")
        nb_lay = QVBoxLayout(notes_box)
        self._render_note_section(nb_lay, "notes", "یادداشت:")
        self._render_note_section(nb_lay, "reminder_notes", "یادداشت یادآوری:")
        vwrap.addWidget(notes_box)

        # فایل‌ها (RTL & راست‌چین)
        files_box = QGroupBoxEx("فایل‌های آپلودی")
        fb_lay = QVBoxLayout(files_box)
        self._render_files_section(fb_lay, "uploaded_files", "پرونده:")
        self._render_files_section(fb_lay, "petition_uploaded_files", "دادخواست:")
        vwrap.addWidget(files_box)

        # سایر فیلدها (RTL & راست‌چین)
        all_box = QGroupBoxEx("همهٔ فیلدهای رکورد")
        ab_lay = QVBoxLayout(all_box)
        self._render_all_fields(ab_lay)
        vwrap.addWidget(all_box, 1)

        self.scroll.setWidget(wrap)
        root.addWidget(self.scroll, 1)

        # دکمه «بستن» حذف شد

    # ---------- helpers UI ----------

    def _open_next_reminder_dialog(self):
        # مقدار اولیه از last_action_date بارگذاری می‌شود
        initial = str(self.rec.get("last_action_date", "")).strip()
        dlg = NextReminderDialog(initial_value=initial, parent=self)
        if dlg.exec() == QDialog.Accepted:
            new_val = dlg.get_value().strip()
            # فقط اگر تغییر کرده باشد ذخیره و ارسال شود
            if new_val != initial:
                self.rec["last_action_date"] = new_val
                self._save_and_sync(self.rec)

    def _open_reminder_dialog(self):
        dlg = ReminderSettingsDialog(self.rec, save_callback=self._save_and_sync, parent=self)
        dlg.exec()

    def _save_and_sync(self, rec: dict):
        self.records[self.rec_index] = rec
        self._save_fn()
        rec_id = rec.get("id", "")
        self._sync_fn(rec_id)

    def _on_delete(self):
        name = self.rec.get("company_name", "(بدون نام)")
        if QMessageBox.question(self, "حذف پرونده",
                                f"آیا از حذف پرونده «{name}» مطمئن هستید؟ این عملیات قابل بازگشت نیست.",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            rec_id = str(self.rec.get("id",""))
            self._delete_fn(self.rec_index, rec_id)
            self.accept()

    def _open_editor(self):
        """باز کردن ویرایشگر به‌شکل «کاملاً مودال» و با پارامترهای درست شیت."""
        try:
            try:
                from ui import editor_window as ew
            except Exception:
                import editor_window as ew
    
            creator = getattr(ew, 'EditorWindow', None)
            if creator is None:
                raise ImportError('EditorWindow not found in editor_window.py')
    
            rid = str(self.rec.get('id') or '').strip()
            if not rid:
                QMessageBox.critical(self, 'خطا', 'این رکورد شناسه (id) ندارد.')
                return
    
            dlg = QDialog(self)
            dlg.setObjectName('EditorDialog')
            dlg.setWindowTitle('ویرایش')
            dlg.setWindowModality(Qt.ApplicationModal)
            dlg.setModal(True)
            dlg.setAttribute(Qt.WA_DeleteOnClose, True)
            _layout = QVBoxLayout(dlg)
    
            # سعی می‌کنیم با API جدید باز کنیم:
            try:
                w = creator(
                    record_id=rid,
                    parent=dlg,
                )
            except TypeError:
                # پشتیبانی از API قدیمی:
                try:
                    w = creator(replace_index=self.rec_index, parent=dlg)
                except TypeError:
                    # آخرین تلاش‌ها: امضاهای ساده‌تر
                    for make in (
                        lambda: creator(record=self.rec, parent=dlg),
                        lambda: creator(data=self.rec, parent=dlg),
                        lambda: creator(self.rec, parent=dlg),
                        lambda: creator(parent=dlg),
                        lambda: creator(),
                    ):
                        try:
                            w = make()
                            break
                        except TypeError:
                            w = None
                            continue
                    if w is None:
                        raise RuntimeError('سازندهٔ EditorWindow شناخته نشد.')
    
            try:
                w.setParent(dlg)
            except Exception:
                pass
            # راست‌چین و استایل یکسان با نسخهٔ قبلی
            try:
                w.setLayoutDirection(Qt.RightToLeft)
                w.setLocale(QtCore.QLocale(QtCore.QLocale.Persian, QtCore.QLocale.Iran))
            except Exception:
                pass
            # اگر QSS سفارشی داری، روی دیالوگ اعمال می‌شود تا به همهٔ فرزندان برسد
            try:
                if os.path.exists(ABBASPOOR_QSS):
                    with open(ABBASPOOR_QSS, 'r', encoding='utf-8') as _f:
                        dlg.setStyleSheet(_f.read())
            except Exception:
                pass
            # هم‌ترازسازی فرم‌ها
            try:
                for _fl in w.findChildren(QFormLayout):
                    _fl.setFormAlignment(Qt.AlignRight | Qt.AlignTop)
                    _fl.setLabelAlignment(Qt.AlignRight)
            except Exception:
                pass

            except Exception:
                pass
    
            _layout.addWidget(w)
            dlg.resize(860, 1140)
            dlg.exec()
    
        except SystemExit:
            QMessageBox.critical(self, 'خطا', 'editor_window.py هنگام import اجرا شد. پردازش آرگومان فقط داخل __main__ باشد.')
        except Exception as e:
            # فالبک: اجرا در پردازهٔ جدا (مودالِ کامل نیست)
            path = os.path.join(_PROJECT_ROOT, 'ui', 'editor_window.py')
            if not os.path.exists(path):
                path = os.path.join(_PROJECT_ROOT, 'editor_window.py')
            if os.path.exists(path):
                try:
                    QMessageBox.information(self, 'توجه', 'ویرایشگر در یک پردازهٔ جدا باز می‌شود و مودالِ کامل نخواهد بود.')
                    subprocess.Popen([sys.executable, path,
                                       '--record-id', rid], cwd=_PROJECT_ROOT)
                except Exception as e2:
                    QMessageBox.critical(self, 'خطا', 'باز کردن ویرایشگر ناموفق بود:\n' + str(e2))
            else:
                QMessageBox.critical(self, 'خطا', 'editor_window.py پیدا نشد.')
    def _ensure_list(self, v):
        if v in (None, ""): return []
        return v if isinstance(v, list) else [str(v)]

    def _render_note_section(self, parent_layout: QVBoxLayout, key: str, title_text: str):
        rec_list = self._ensure_list(self.rec.get(key))
        box = QWidget(); box.setLayoutDirection(Qt.RightToLeft)
        v = QVBoxLayout(box); v.setContentsMargins(0,0,0,0); v.setSpacing(6)
        title = QLabel(title_text); title.setProperty("boldLabel", True)
        title.setAlignment(Qt.AlignRight)
        v.addWidget(title, 0, Qt.AlignRight)
        if not rec_list:
            hint = QLabel("(یادداشتی ثبت نشده)"); hint.setStyleSheet("color:#777;")
            hint.setAlignment(Qt.AlignRight)
            v.addWidget(hint, 0, Qt.AlignRight)
        for i, text in enumerate(rec_list):
            row = QHBoxLayout()
            l = QLabel("• " + str(text)); l.setWordWrap(True); l.setAlignment(Qt.AlignRight)
            row.addWidget(l, 1, Qt.AlignRight)
            btn_edit = QPushButton("ویرایش")
            btn_del  = QPushButton("حذف")
            btn_edit.clicked.connect(lambda _, idx=i, k=key: self._edit_note(k, idx))
            btn_del.clicked.connect(lambda _, idx=i, k=key: self._delete_note(k, idx))
            row.addWidget(btn_del, 0, Qt.AlignLeft)
            row.addWidget(btn_edit, 0, Qt.AlignLeft)
            v.addLayout(row)
        add_btn = QPushButton("افزودن یادداشت")
        add_btn.clicked.connect(lambda _, k=key: self._add_note(k))
        v.addWidget(add_btn, 0, Qt.AlignLeft)
        parent_layout.addWidget(box)

    def _add_note(self, key: str):
        dlg = NoteEditDialog("افزودن یادداشت", "", self)
        if dlg.exec() == QDialog.Accepted:
            text = dlg.get_text()
            arr = self._ensure_list(self.rec.get(key))
            if text: arr.append(text)
            self.rec[key] = arr
            self._save_and_sync(self.rec)
            self._refresh_self()

    def _edit_note(self, key: str, idx: int):
        arr = self._ensure_list(self.rec.get(key))
        cur = arr[idx] if 0 <= idx < len(arr) else ""
        dlg = NoteEditDialog("ویرایش یادداشت", str(cur), self)
        if dlg.exec() == QDialog.Accepted:
            text = dlg.get_text()
            if text: arr[idx] = text
            else:    arr.pop(idx)
            if arr:  self.rec[key] = arr
            else:    self.rec.pop(key, None)
            self._save_and_sync(self.rec)
            self._refresh_self()

    def _delete_note(self, key: str, idx: int):
        arr = self._ensure_list(self.rec.get(key))
        if 0 <= idx < len(arr):
            arr.pop(idx)
            if arr:  self.rec[key] = arr
            else:    self.rec.pop(key, None)
            self._save_and_sync(self.rec)
            self._refresh_self()

    def _refresh_self(self):
        idx = self.rec_index
        recs = self.records
        save_fn = self._save_fn
        sync_fn = self._sync_fn
        del_fn  = self._delete_fn
        self.close()
        d = DetailsDialog(self.parent(), idx, recs, save_fn, sync_fn, del_fn)
        d.exec()

    # ---------- files ----------
    def _render_files_section(self, parent_layout: QVBoxLayout, key_name: str, title: str):
        pairs = _normalize_files_list(self.rec.get(key_name) or [])
        box = QWidget(); box.setLayoutDirection(Qt.RightToLeft)
        v = QVBoxLayout(box); v.setContentsMargins(0,0,0,0); v.setSpacing(6)
        lbl = QLabel(title); lbl.setProperty("boldLabel", True); lbl.setAlignment(Qt.AlignRight)
        v.addWidget(lbl, 0, Qt.AlignRight)
        if not pairs:
            hint = QLabel("فایلی آپلود نشده است."); hint.setStyleSheet("color:#777;"); hint.setAlignment(Qt.AlignRight)
            v.addWidget(hint, 0, Qt.AlignRight)
        for name, url in pairs:
            row = QHBoxLayout()
            link = QtWidgets.QCommandLinkButton(name)
            link.setCursor(Qt.PointingHandCursor)
            link.setLayoutDirection(Qt.RightToLeft)
            link.clicked.connect(lambda _, u=url: self._open_or_download(u))
            row.addWidget(link, 1, Qt.AlignRight)
            btn_del = QPushButton("حذف")
            btn_del.clicked.connect(lambda _, n=name, u=url, k=key_name: self._remove_file(k, n, u))
            row.addWidget(btn_del, 0, Qt.AlignLeft)
            v.addLayout(row)
        buttons = QHBoxLayout()
        add_file = QPushButton("افزودن فایل")
        add_url  = QPushButton("افزودن URL")
        add_file.clicked.connect(lambda _, k=key_name: self._add_file_local(k))
        add_url.clicked.connect(lambda _, k=key_name: self._add_file_url(k))
        buttons.addWidget(add_file, 0, Qt.AlignLeft)
        buttons.addWidget(add_url,  0, Qt.AlignLeft)
        v.addLayout(buttons)
        parent_layout.addWidget(box)

    def _open_or_download(self, locator: str):
        s = (locator or "").strip()
        if not s:
            QMessageBox.warning(self, "خطا", "آدرس/مسیر فایل معتبر نیست.")
            return
        p = urllib.parse.urlparse(s)
        if p.scheme in ("http", "https", "ftp"):
            filename = os.path.basename(p.path) or "download"
            save, _ = QFileDialog.getSaveFileName(self, "ذخیره فایل", filename, "All files (*.*)")
            if not save: return
            try:
                urllib.request.urlretrieve(s, save)
                QMessageBox.information(self, "دانلود شد", f"فایل ذخیره شد:\n{save}")
            except Exception as e:
                QMessageBox.critical(self, "خطا در دانلود", str(e))
            return
        if p.scheme == "file":
            local = urllib.parse.unquote(p.path)
            if os.name == "nt" and local.startswith("/"):
                local = local.lstrip("/")
            self._copy_local_path(local)
            return
        if re.match(r'^[A-Za-z]:[\\\\/]', s) or s.startswith('\\\\'):
            self._copy_local_path(s)
            return
        QDesktopServices.openUrl(QUrl(s))

    def _copy_local_path(self, local: str):
        base = os.path.basename(local)
        save, _ = QFileDialog.getSaveFileName(self, "ذخیره کپی فایل", base, "All files (*.*)")
        if not save: return
        try:
            shutil.copyfile(local, save)
            QMessageBox.information(self, "کپی شد", f"فایل ذخیره شد:\n{save}")
        except Exception as e:
            QMessageBox.critical(self, "خطا در کپی", str(e))

    def _remove_file(self, key_name: str, name: str, url: str):
        items = _normalize_files_list(self.rec.get(key_name) or [])
        items = [(n,u) for (n,u) in items if not (n==name and u==url)]
        if items:
            self.rec[key_name] = [{"name": n, "url": u} for (n,u) in items]
        else:
            self.rec.pop(key_name, None)
        self._save_and_sync(self.rec)

    def _add_file_local(self, key_name: str):
        # دیالوگ انتخاب فایل – می‌تونی اینجا UPLOAD_ROOT رو بذاری که دیفالت روی همون پوشه باز بشه
        path, _ = QFileDialog.getOpenFileName(self, "افزودن فایل",UPLOAD_ROOT, "All files (*.*)")
        if not path:
            return

        # نام فایل اصلی
        base_name = _basename_only(path)

        # اسم یکتا برای کپی داخل پوشه آپلود (تا رو هم نیوفتن)
        stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        name_with_stamp = f"{os.path.splitext(base_name)[0]}_{stamp}{os.path.splitext(base_name)[1]}"
        dest = os.path.join(UPLOAD_ROOT, name_with_stamp)

        # کپی کردن فایل به پوشه‌ی آپلود
        try:
            shutil.copy2(path, dest)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در کپی فایل به پوشه آپلود:\n{e}")
            return

        # لیست فعلی فایل‌ها را بگیر
        pairs = _normalize_files_list(self.rec.get(key_name) or [])

        # اگر همین dest قبلاً تو لیست هست، تکراری حسابش کن
        if any(u == dest for _, u in pairs):
            QMessageBox.warning(self, "تکراری", "این فایل قبلاً اضافه شده است.")
            return

        # نام نمایشی = name_with_stamp ، مسیر واقعی = dest
        pairs.append((name_with_stamp, dest))
        self.rec[key_name] = [{"name": n, "url": u} for (n, u) in pairs]
        self._save_and_sync(self.rec)
    def _add_file_url(self, key_name: str):
        dlg = UrlAddDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return

        url = dlg.get_url()
        if not url:
            return

        # اسم پایه از روی URL
        parsed = urllib.parse.urlparse(url)
        base_name = os.path.basename(parsed.path) or "download"

        # اضافه کردن تایم‌استمپ برای یکتا شدن اسم
        stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        name_with_stamp = f"{os.path.splitext(base_name)[0]}_{stamp}{os.path.splitext(base_name)[1]}"
        dest = os.path.join(UPLOAD_ROOT, name_with_stamp)

        # دانلود فایل به Z:\uploads
        try:
            urllib.request.urlretrieve(url, dest)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"دانلود فایل از URL ناموفق بود:\n{e}")
            return

        pairs = _normalize_files_list(self.rec.get(key_name) or [])

        # بر اساس مسیر مقصد (داخل Z:\uploads) چک تکراری بودن
        if any(u == dest for _, u in pairs):
            QMessageBox.warning(self, "تکراری", "این فایل قبلاً اضافه شده است.")
            return

        # name = اسم فایل ذخیره شده، url = مسیر لوکال تو Z:\uploads
        pairs.append((name_with_stamp, dest))
        self.rec[key_name] = [{"name": n, "url": u} for (n, u) in pairs]
        self._save_and_sync(self.rec)
    
    
    def _render_all_fields(self, parent_layout: QVBoxLayout):
        table = QTableWidget()
        keys = []
        seen = set()
        # نگاشت بدون حساسیت به حروف برای هم‌ترازی با هدر شیت
        rec_map = {str(k).lower(): k for k in self.rec.keys()}
        # اول براساس هدر شیت
        for h in (self.header_order or []):
            hk = str(h).lower()
            if hk in rec_map and rec_map[hk] not in seen:
                keys.append(rec_map[hk]); seen.add(rec_map[hk])
        # سپس سایر کلیدهای رکورد
        for k in self.rec.keys():
            if k not in seen:
                keys.append(k); seen.add(k)

        table.setRowCount(len(keys))
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["فیلد", "مقدار"])
        table.verticalHeader().setVisible(False)
        table.setShowGrid(True)
        table.setWordWrap(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.setAlternatingRowColors(True)

        for r, k in enumerate(keys):
            v = self.rec.get(k)
            key_item = QTableWidgetItem(fa_label(str(k)))
            key_item.setFlags(key_item.flags() ^ Qt.ItemIsEditable)
            val_item = QTableWidgetItem(_format_value(v))
            val_item.setFlags(val_item.flags() ^ Qt.ItemIsEditable)
            table.setItem(r, 0, key_item)
            table.setItem(r, 1, val_item)

        parent_layout.addWidget(table)




# ================ ویجت اصلی (لیست کارت‌ها) ================
class App3Widget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TaxDashboardPage")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet("""
        #CardFrame {border:1px solid rgba(255,255,255,0.10); border-radius:8px;}
        #CardFrame QLabel[cardTitle="true"] {font-weight:600;}
        """)

        self.records: List[Dict[str, Any]] = []

        self._query: str = ""
        self.SEARCH_MODE: str = "contains"
        self.SEARCH_FIELDS: Tuple[str, ...] = ("company_name",)
        self._company_names_cache: List[str] = []

        self._build_ui()
        self._apply_style()
        self._load_json_and_refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 8, 16, 16)
        root.setSpacing(10)

        title = QLabel("پرونده شرکت‌ها")
        title.setProperty("cardTitle", True)
        root.addWidget(title, 0, Qt.AlignRight)

        search_row = QHBoxLayout()
        search_row.addStretch(1)
        self.search_combo = QComboBox()
        self.search_combo.setEditable(True)
        self.search_combo.setInsertPolicy(QComboBox.NoInsert)
        self.search_combo.lineEdit().setPlaceholderText("نام شرکت را بنویسید یا انتخاب کنید…")
        self.search_combo.setMinimumWidth(300)
        self.btn_clear_search = QToolButton()
        self.btn_clear_search.setText("×")
        self.btn_clear_search.setToolTip("پاک کردن جستجو")
        self.btn_clear_search.setCursor(Qt.PointingHandCursor)
        self.btn_clear_search.clicked.connect(lambda: self.search_combo.setCurrentText(""))
        search_row.addWidget(self.search_combo, 0, Qt.AlignRight)
        search_row.addWidget(QLabel("نام شرکت:"), 0, Qt.AlignRight)
        search_row.addSpacing(6)
        search_row.addWidget(self.btn_clear_search, 0, Qt.AlignRight)

        self.btn_refresh = QToolButton()
        self.btn_refresh.setText("↻")
        self.btn_refresh.setToolTip("تازه‌سازی از Google Sheet")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setShortcut(Qt.Key_F5)
        try:
            self.btn_refresh.clicked.connect(self._on_refresh_clicked)
        except Exception:
            pass
        search_row.addWidget(self.btn_refresh, 0, Qt.AlignRight)
        root.addLayout(search_row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(520)
        self.scroll.setObjectName("CardsScroll")
        self.cards_host = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_host)
        self.cards_layout.setContentsMargins(0, 6, 0, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch(1)
        self.scroll.setWidget(self.cards_host)
        root.addWidget(self.scroll, 1)

        self.status = QLabel("")
        root.addWidget(self.status, 0, Qt.AlignRight)

        
        # ---- فرم‌بندی کل صفحه برای خوانایی بهتر ----
        form = QGroupBoxEx("")
        vform = QVBoxLayout(form)
        vform.setContentsMargins(12,12,12,12)
        vform.setSpacing(10)
        # انتقال همه آیتم‌های فعلی root به داخل فرم
        moved_items = []
        while root.count():
            it = root.takeAt(0)
            if it.widget():
                moved_items.append(it.widget())
            elif it.layout():
                vform.addLayout(it.layout())
        for w in moved_items:
            vform.addWidget(w)
        root.addWidget(form, 1)
        try:
            self.search_combo.currentTextChanged.connect(self._on_search_changed)
            self.search_combo.lineEdit().returnPressed.connect(lambda: self._on_search_changed(self.search_combo.currentText()))
        except Exception:
            pass

        self.sheet_status = QLabel("")
        root.addWidget(self.sheet_status, 0, Qt.AlignLeft)
    def _apply_style(self):
        qss = ""
        try:
            with open(ABBASPOOR_QSS, "r", encoding="utf-8") as f:
                qss = f.read()
        except Exception as e:
            print("⚠️ استایل سفارشی لود نشد:", e)
        EXTRA = """
        [cardTitle="true"] { color:#F5F5F5; font-weight:700; font-size:16px; }
        [boldLabel="true"] { font-weight:600; }

        QFrame#CardFrame {
            background: rgba(255,255,255,0.03);
            border: 1px solid #383838;
            border-radius: 12px;
        }
        QFrame#CardFrame:hover { border-color: #FFFFFF; }

        QPushButton#CardActionBtn {
            border:1px solid #383838; border-radius:16px; background:#2C2E33;
            color:#F5F5F5; padding:6px 12px; min-width:110px;
        }
        QPushButton#CardActionBtn:hover { border-color:#FFFFFF; }

        QScrollArea#CardsScroll { border:none; }

        QComboBox::drop-down { width:24px; border:none; }
        QSpinBox::up-button, QSpinBox::down-button { width:24px; }
        """
        self.setStyleSheet(qss + "\n" + EXTRA)

    def _load_json_and_refresh(self):
        """بارگذاری فایل‌ها از دیتابیس TaxFileDB"""
        try:
            self.records = load_files()
            if self.records:
                try:
                    self._populate_search_sources()
                    self._on_search_changed(self.search_combo.currentText())
                except Exception:
                    self._render_all_cards()
                self.status.setText(f"{len(self.records)} فایل از دیتابیس خوانده شد.")
                return
        except Exception as e:
            self.status.setText(f"⚠️ خواندن از دیتابیس ناموفق: {e}")
            self.records = []

    def _load_json(self, path) -> Tuple[bool, str]:
        """برای سازگاری: دیتابیس اصلی است، JSON استفاده نمی‌شود"""
        return True, "OK"

    def _save_json(self):
        """برای سازگاری: ذخیره به دیتابیس انجام می‌شود"""
        pass

    def _ensure_ids_for_all_records(self) -> int:
        """تمام رکوردها از دیتابیس آمده‌اند و ID دارند"""
        return 0

    def _clear_cards(self):
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _populate_search_sources(self):
        names = sorted({str(r.get("company_name","")).strip() for r in self.records if r.get("company_name")})
        self._company_names_cache = [n for n in names if n]
        try:
            self.search_combo.blockSignals(True)
            self.search_combo.clear()
            self.search_combo.addItem("")
            for n in self._company_names_cache:
                self.search_combo.addItem(n)
            self.search_combo.blockSignals(False)
            comp = QtWidgets.QCompleter(self._company_names_cache, self.search_combo)
            comp.setCaseSensitivity(Qt.CaseInsensitive)
            self.search_combo.setCompleter(comp)
        except Exception:
            pass

    def _on_search_changed(self, text: str):
        self._query = (text or "").strip()
        self._render_all_cards()

    def _filtered_records(self) -> List[Dict[str, Any]]:
        if not self._query:
            return self.records
        matches = search_records(self.records, self._query, mode=self.SEARCH_MODE, fields=self.SEARCH_FIELDS)
        if not matches:
            return []
        idxs = [i for i, _ in matches]
        return [self.records[i] for i in idxs]

    def _render_all_cards(self):
        self._clear_cards()
        data = self._filtered_records() if hasattr(self, "_filtered_records") else self.records

        if not self.records:
            self.status.setText("پرونده‌ای یافت نشد.")
            return
        if hasattr(self, "_query") and self._query and not data:
            self.status.setText("0 نتیجه.")
            return

        for idx, r in enumerate(data):
            card = CompanyCardWidget(
                company=r.get("company_name","—"),
                fiscal_year=str(r.get("fiscal_year","—")),
                entry_date=r.get("entry_date","—"),
                last_action_date=r.get("last_action_date","—"),
                case_type=r.get("case_type","—"),
                status=r.get("status","—"),
                parent=self.cards_host
            )
            real_index = self.records.index(r) if r in self.records else idx
            card.clickedDetails.connect(lambda i=real_index: self._open_details(i))
            self.cards_layout.insertWidget(self.cards_layout.count()-1, card, 0, Qt.AlignTop)

        if hasattr(self, "_query") and self._query:
            self.status.setText(f"{len(data)} نتیجه یافت شد.")
        else:
            self.status.setText(f"{len(self.records)} رکورد نمایش داده شد.")

    def _open_details(self, rec_index: int):
        dlg = DetailsDialog(self, rec_index, self.records, self._save_json, self._sync_record_to_db_by_id, self._delete_record, header_order=None)
        dlg.exec()

    def _sync_record_to_db_by_id(self, rec_id: str):
        if not rec_id:
            return
        try:
            rec = next((x for x in self.records if str(x.get("id","")) == str(rec_id)), None)
            if not rec:
                return
            self.sheet_status.setText("در حال ارسال به دیتابیس…")
            save_file(rec)
            self.sheet_status.setText(f"✅ با موفقیت ذخیره شد (ID: {rec_id})")
        except Exception as e:
            self.sheet_status.setText(f"❌ خطا در ذخیره‌سازی: {e}")

    def _delete_record(self, rec_index: int, rec_id: str):
        try:
            self.records.pop(rec_index)
            self._save_json()
            if rec_id:
                try:
                    delete_file(rec_id)
                    self.sheet_status.setText(f"🗑️ فایل با ID {rec_id} حذف شد.")
                except Exception as e:
                    self.sheet_status.setText(f"❌ خطا در حذف: {e}")
            try:
                self._populate_search_sources()
                self._on_search_changed(self._query)
            except Exception:
                self._render_all_cards()
            QMessageBox.information(self, "حذف شد", "پرونده با موفقیت حذف شد.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"حذف ناموفق بود:\n{e}")

# --------- گروه‌باکس با ظاهر هماهنگ ---------

    def _on_refresh_clicked(self):
        btn = getattr(self, 'btn_refresh', None)
        if btn:
            btn.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self._load_json_and_refresh()
            self.sheet_status.setText(f"✓ دیتابیس فعال")
        except Exception as e:
            QMessageBox.warning(self, "تازه‌سازی ناموفق", str(e))
        finally:
            QApplication.restoreOverrideCursor()
            if btn:
                btn.setEnabled(True)
class QGroupBoxEx(QtWidgets.QGroupBox):
    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setStyleSheet("""
        QGroupBox {
            border:1px solid #383838; border-radius:10px; margin-top:8px; padding:8px 8px 8px 8px;
        }
        QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top right; padding: 0 4px; }
        """)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet("""
        #CardFrame {border:1px solid rgba(255,255,255,0.10); border-radius:8px;}
        #CardFrame QLabel[cardTitle="true"] {font-weight:600;}
        """)


# ================ اجرای مستقل برای تست ================
def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    w = App3Widget()
    w.resize(980, 720)
    w.setWindowTitle("پرونده شرکت‌ها - شهر ارقام")
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()