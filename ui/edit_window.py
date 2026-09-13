import os


# --- Robust Service Account resolver (works for .py and PyInstaller EXE) ---
def _resolve_service_account(creds_path: str):
    """
    Return a tuple (kind, src) where:
      - kind is 'file' or 'inline'
      - src is a filesystem path (for kind=='file') or a dict loaded from JSON (for kind=='inline')
    Resolution order:
      1) env path: GOOGLE_CREDS_JSON or GOOGLE_SA_JSON pointing to a readable file
      2) provided creds_path (file)
      3) bundle sidecar file next to the EXE (sys._MEIPASS or argv[0]) named 'google-service-account.json'
      4) inline JSON from env: GOOGLE_CREDS_JSON_INLINE or GOOGLE_SA_JSON_INLINE
    """
    import os, sys, json

    # 1) env path variables
    for env_name in ("GOOGLE_CREDS_JSON", "GOOGLE_SA_JSON"):
        env_path = os.environ.get(env_name)
        if env_path and os.path.isfile(env_path):
            return "file", env_path

    # 2) explicit argument path
    if creds_path and os.path.isfile(creds_path):
        return "file", creds_path

    # 3) PyInstaller bundle or app dir sidecar
    base_dir = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(sys.argv[0] or __file__))
    cand = os.path.join(base_dir, "google-service-account.json")
    if os.path.isfile(cand):
        return "file", cand

    # 4) inline JSON via env
    for env_inline in ("GOOGLE_CREDS_JSON_INLINE", "GOOGLE_SA_JSON_INLINE", "GOOGLE_SA_JSON"):
        blob = os.environ.get(env_inline)
        if blob:
            try:
                data = json.loads(blob)
                if isinstance(data, dict) and "client_email" in data and "private_key" in data:
                    return "inline", data
            except Exception:
                pass

    raise RuntimeError("Service Account JSON یافت نشد. فایل را کنار برنامه قرار دهید یا متغیرهای "
                       "GOOGLE_CREDS_JSON / GOOGLE_SA_JSON (مسیر فایل) یا "
                       "GOOGLE_CREDS_JSON_INLINE / GOOGLE_SA_JSON_INLINE (JSON inline) را ست کنید.")


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os, argparse, json, shutil, datetime, time, random
import jdatetime
from typing import Dict, Any, List
from contextlib import suppress

# ============ مسیر پروژه ============
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ================= PySide6 =================
from PySide6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QPushButton, QMessageBox, QLabel, QHBoxLayout, QTextEdit, QFrame,
    QFileDialog, QListWidget, QListWidgetItem, QRadioButton, QButtonGroup, QGroupBox,
    QComboBox, QScrollArea, QDialog, QApplication, QCheckBox, QDoubleSpinBox,
    QAbstractSpinBox, QDateEdit, QDateTimeEdit, QPlainTextEdit
)
from prefill_helpers import prefill_editor_window

from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression, Qt, QTimer


# --- injected helpers for read-only visual state ---
def _readonly_look_widget(w):
    """Make a widget read-only but keep theme colors. Hide spin buttons if available."""
    try:
        from PySide6.QtWidgets import QLineEdit, QSpinBox, QDateEdit, QAbstractSpinBox
    except Exception:
        return
    try:
        if isinstance(w, QLineEdit):
            w.setReadOnly(True)
            # Do NOT set stylesheet/background; keep theme colors
            return
        if isinstance(w, (QSpinBox, QDateEdit)):
            try:
                w.setReadOnly(True)
            except Exception:
                pass
            try:
                w.setButtonSymbols(QAbstractSpinBox.NoButtons)
            except Exception:
                pass
            # Keep theme; no stylesheet here
            return
    except Exception:
        pass

def _dim_label_for_widget_in_form(self, w):
    """Find the label for a given field in self.form (QFormLayout) and dim it using theme (disabled state)."""
    try:
        from PySide6.QtWidgets import QFormLayout, QLabel
    except Exception:
        return
    try:
        form = getattr(self, "form", None)
        if isinstance(form, QFormLayout):
            lbl = form.labelForField(w)
            if isinstance(lbl, QLabel):
                lbl.setEnabled(False)  # dims via theme
                return
        # Fallback: search all QFormLayout children
        for fl in self.findChildren(QFormLayout):
            lbl = fl.labelForField(w)
            if isinstance(lbl, QLabel):
                lbl.setEnabled(False)
                return
    except Exception:
        pass

def _apply_readonly_fields(self):
    # The specific fields requested to be read-only
    for name in ("company","national_id","archive", "fiscal", "entry", "submit_date", "deadline_days", "due_date"):
        w = getattr(self, name, None)
        if w is not None:
            _readonly_look_widget(w)
            _dim_label_for_widget_in_form(self, w)
    # Disable radio buttons group for case type (and let theme dim them)
    group = getattr(self, "group_case", None)
    if group is not None:
        try:
            for rb in group.buttons():
                rb.setEnabled(False)
        except Exception:
            pass
# --- end injected helpers ---


# اگر این دو پنل را دارید (مثل پروژهٔ اصلی‌تان)، ایمپورت بماند
from widgets.bodavi_panel import BodaviPanel
from widgets.tajdid_panel import TajdidPanel

# ===== مسیرها =====
STORAGE_FILE  = os.path.join(PROJECT_ROOT, 'companies.json')
SETTINGS_FILE = os.path.join(PROJECT_ROOT, 'settings.json')
UPLOAD_ROOT = r"D:\uploads"
os.makedirs(UPLOAD_ROOT, exist_ok=True)
QSS_PATH      = os.path.join(PROJECT_ROOT, 'styles', 'abbaspoor.qss')


# ===== تنظیمات Google Sheets از محیط =====
GOOGLE_SHEETS_KEY = os.getenv("GOOGLE_SHEETS_KEY", "1wZ0Hbml_NUqYOeMm8NyeR60uFBhFMJl5zIz2fTM7EbQ").strip()
GOOGLE_SA_JSON    = os.getenv("GOOGLE_SA_JSON",  os.path.join(PROJECT_ROOT, "google-service-account.json")).strip()
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Sheet1").strip()

# اگر شیت خالی باشد این هدر پیش‌فرض نوشته می‌شود (با «id» در ستون A).
DEFAULT_HEADER = [
    "id",
    "company_name",
    "fiscal_year",
    "case_type",
    "entry_date",
    "submit_date",
    "deadline_days",
    "due_date",
    "submit_status",
    "upload_date",
    "uploaded_files",
    "has_assessment",
    "assessment_date",
    "assessment_deadline",
    "report_exists",
    "objected",
    "appeal_send_date",
    "petition_uploaded_files",
    "mad238_entry_date",
    "mad238_agreement_deadline",
    "jarime_amount",
    "performance_penalty",
    "vat_p1_tax", "vat_p1_penalty",
    "vat_p2_tax", "vat_p2_penalty",
    "vat_p3_tax", "vat_p3_penalty",
    "vat_p4_tax", "vat_p4_penalty",
    "notes",
    "notify_days",
    "notify_mode",
    "mad238_result",
    "bodavi_session_date",
    "bodavi_verdict_date",
    "bodavi_appeal_deadline",
    "bodavi_appeal_done",
    "bodavi_appeal_date",
    "bodavi_verdict",
    "needs_investigation",
    "status",
    "reminder_notes",
    "tajdid_refer_date",
    "verdict_date_tajdid",
    "objection_deadline_tajdid",
    "objection_done_tajdid",
    "objection_date_tajdid",
    "verdict_result_tajdid",
    "verification_status",
    "council_date",
    "needs_investigation_tajdid",
    "last_action_date",
    "final_amount"
]

# ===== کمکی =====
def validate_jalali(s: str) -> bool:
    try:
        jdatetime.datetime.strptime(s, "%Y/%m/%d")
        return True
    except Exception:
        return False

def _load_qss(app: QApplication):
    """لود تم عباسپور بدون تغییر منطق اپ"""
    if os.path.exists(QSS_PATH):
        try:
            with open(QSS_PATH, 'r', encoding='utf-8') as f:
                app.setStyleSheet(f.read())
        except Exception:
            pass

# ===== ارسال/به‌روزرسانی در شیت =====
def upsert_record_to_sheet(rec: dict,
                           spreadsheet_id: str,
                           sa_json_path: str,
                           sheet_name: str,
                           status_label: QLabel | None = None) -> str:
    """
    رکورد را با 'id' پیدا و به‌روز می‌کند؛ در غیر این صورت اضافه می‌کند.
    رفتار برای reminder_notes و notes مثل app2 است:
      - عدم حذف مقدار قبلی
      - ادغام با مقدار جدید
      - ذخیره به صورت JSON لیست (بدون '|')
    """
    try:
        if status_label: status_label.setText("در حال اتصال به Google Sheets…")

        from google.oauth2.service_account import Credentials
        import gspread
        from gspread.utils import rowcol_to_a1
        from gspread.exceptions import APIError
        import time, random, json

        def backoff(fn, *args, **kwargs):
            delay = 1.0
            for _ in range(7):
                try:
                    return fn(*args, **kwargs)
                except APIError as e:
                    code = getattr(getattr(e, "response", None), "status_code", None)
                    msg = str(e).lower()
                    if code in (429, 500, 502, 503, 504) or "quota" in msg or "rate" in msg:
                        time.sleep(delay + random.random())
                        delay = min(delay * 2, 32)
                        continue
                    raise
                except Exception:
                    time.sleep(delay + random.random())
                    delay = min(delay * 2, 32)

        kind, _sa_src = _resolve_service_account(sa_json_path)
        if kind == 'file':
            creds = Credentials.from_service_account_file(_sa_src, scopes=[
"https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
            ])
        else:
            creds = Credentials.from_service_account_info(_sa_src, scopes=[
"https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
            ])
        gc = gspread.authorize(creds)
        sh = backoff(gc.open_by_key, spreadsheet_id)

        # worksheet
        try:
            ws = backoff(sh.worksheet, sheet_name)
        except Exception:
            cols = max(60, len(DEFAULT_HEADER))
            ws = backoff(sh.add_worksheet, title=sheet_name, rows=200, cols=cols)

        # هدر
        if status_label: status_label.setText("همگام‌سازی هدر شیت…")
        hdr = backoff(sh.values_get, f"{sheet_name}!A1:1").get("values", [])
        cur_header = hdr[0] if hdr else []
        if not cur_header:
            last_col_a1 = rowcol_to_a1(1, len(DEFAULT_HEADER))
            last_col = "".join([c for c in last_col_a1 if c.isalpha()])
            body = {"valueInputOption": "USER_ENTERED",
                    "data": [{"range": f"{sheet_name}!A1:{last_col}1", "values": [DEFAULT_HEADER]}]}
            backoff(sh.values_batch_update, body)
            cur_header = DEFAULT_HEADER[:]

        # نرمال‌ساز: هیچ‌وقت '|' تولید نکند
        def norm(v):
            if v is None: return ""
            if isinstance(v, bool): return "TRUE" if v else "FALSE"
            if isinstance(v, (int, float)): return str(v)
            if isinstance(v, list):
                try: return json.dumps(v, ensure_ascii=False)
                except Exception: return str(v)
            if isinstance(v, dict):
                try: return json.dumps(v, ensure_ascii=False)
                except Exception: return str(v)
            return str(v)

        # id
        rec_id = str(rec.get("id") or "").strip()
        if not rec_id:
            raise ValueError("شناسهٔ رکورد (id) موجود نیست؛ امکان به‌روزرسانی در شیت ندارم.")

        # اطمینان از وجود ستون id
        try:
            id_col_index = cur_header.index("id")
        except ValueError:
            cur_header = ["id"] + [h for h in cur_header if h != "id"]
            last_col_a1 = rowcol_to_a1(1, len(cur_header))
            last_col = "".join([c for c in last_col_a1 if c.isalpha()])
            body = {"valueInputOption": "USER_ENTERED",
                    "data": [{"range": f"{sheet_name}!A1:{last_col}1", "values": [cur_header]}]}
            backoff(sh.values_batch_update, body)
            id_col_index = 0

        # نقشه id→row
        if status_label: status_label.setText("جستجوی سطر مربوط به id…")
        from gspread.utils import rowcol_to_a1 as _rowcol_to_a1_inner
        first_col_letter = _rowcol_to_a1_inner(1, id_col_index+1).rstrip("1")
        id_col_range = f"{sheet_name}!{first_col_letter}2:{first_col_letter}"
        id_col_vals = backoff(sh.values_get, id_col_range).get("values", [])
        id_to_row = {}
        for i, row in enumerate(id_col_vals, start=2):
            if row and str(row[0]).strip():
                id_to_row[str(row[0]).strip()] = i

        # آماده‌سازی ردیف خروجی
        row_values = [norm(rec.get(key)) for key in cur_header]

        # ابزار تبدیل به لیست (برای parse مقدار قبلی/جدید)
        def to_list(x):
            if x is None: return []
            if isinstance(x, list): return [str(s).strip() for s in x if str(s).strip()]
            s = str(x).strip()
            if not s: return []
            # تلاش JSON
            try:
                jv = json.loads(s)
                if isinstance(jv, list):
                    return [str(t).strip() for t in jv if str(t).strip()]
            except Exception:
                pass
            # fallback: اگر قبلاً با '|' ذخیره شده بود، بخوانیم (اما هرگز ننویسیم)
            return [t.strip() for t in s.split('|')] if '|' in s else [s]

        # کلیدهایی که باید مثل app2 رفتار کنند
        merge_keys = ["reminder_notes", "notes"]

        if rec_id in id_to_row:
            # --- UPDATE: ادغام با مقدار قبلی و ذخیرهٔ JSON ---
            r = id_to_row[rec_id]
            for k in merge_keys:
                if k in cur_header:
                    idx = cur_header.index(k)
                    incoming = to_list(rec.get(k))
                    # مقدار قبلی
                    col_letter = _rowcol_to_a1_inner(1, idx+1).rstrip("1")
                    prev_range = f"{sheet_name}!{col_letter}{r}:{col_letter}{r}"
                    prev_vals = backoff(sh.values_get, prev_range).get("values", [])
                    prev_raw = prev_vals[0][0] if prev_vals and prev_vals[0] else ""
                    prev_list = to_list(prev_raw)
                    # اگر ورودی جدید خالی است، همان قبلی را بنویس (عدم پاک‌کردن)
                    if not incoming:
                        row_values[idx] = json.dumps(prev_list, ensure_ascii=False)
                    else:
                        merged, seen = [], set()
                        for it in prev_list + incoming:
                            if it and it not in seen:
                                seen.add(it)
                                merged.append(it)
                        row_values[idx] = json.dumps(merged, ensure_ascii=False)
        else:
            # --- INSERT: اگر لیست دادی، JSON ذخیره کن؛ نه '|'
            for k in merge_keys:
                if k in cur_header:
                    idx = cur_header.index(k)
                    row_values[idx] = json.dumps(to_list(rec.get(k)), ensure_ascii=False)

        # نوشتن
        last_col_a1 = _rowcol_to_a1_inner(1, len(cur_header))
        last_col = "".join([c for c in last_col_a1 if c.isalpha()])

        if rec_id in id_to_row:
            r = id_to_row[rec_id]
            body = {"valueInputOption": "USER_ENTERED",
                    "data": [{"range": f"{sheet_name}!A{r}:{last_col}{r}", "values": [row_values]}]}
            if status_label: status_label.setText("به‌روزرسانی سطر موجود در شیت…")
            backoff(sh.values_batch_update, body)
            return "updated"
        else:
            params = {"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"}
            body = {"values": [row_values]}
            if status_label: status_label.setText("افزودن سطر جدید به شیت…")
            backoff(sh.values_append, f"{sheet_name}!A1", params, body)
            return "inserted"

    except Exception as e:
        if status_label:
            status_label.setText(f"خطا در ارسال به شیت: {e}")
        raise
# ===== ویجت یادداشت =====
class DynamicNotesWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("AbbaspoorPage")
        self.layout = QVBoxLayout(self)
        self.entries = []
        btn = QPushButton("➕ افزودن یادداشت")
        btn.clicked.connect(lambda: self.add_note(""))
        self.layout.addWidget(btn)
    def add_note(self, text:str):
        frame = QFrame(); frame.setObjectName("NoteCard")
        h = QHBoxLayout(frame)
        te = QTextEdit(); te.setObjectName("NoteText"); te.setFixedHeight(60); te.setPlainText(text)
        btn_del = QPushButton("🗑️"); btn_del.setObjectName("DelNote")
        btn_del.clicked.connect(lambda _,f=frame: self.remove_note(f))
        h.addWidget(te); h.addWidget(btn_del); self.layout.addWidget(frame)
        self.entries.append((frame, te))
    def remove_note(self, frame):
        for f, te in list(self.entries):
            if f is frame:
                self.entries.remove((f,te))
                f.setParent(None)
                return
    def get_notes(self):
        return [te.toPlainText().strip() for _, te in self.entries if te.toPlainText().strip()]
    def clear_all(self):
        for f, te in list(self.entries):
            f.setParent(None)
        self.entries.clear()

# ===== دیالوگ‌ها مختصر =====
class NextReminderDialog(QDialog):
    def __init__(self, parent=None, status=""):
        super().__init__(parent)
        self.status = status or ""
        self.setWindowTitle("تاریخ یادآوری بعدی" if not status else status)
        self.resize(360, 340)
        form = QFormLayout(self)
        self.date = QLineEdit(self); self.date.setInputMask("0000/00/00;_")
        form.addRow("تاریخ:", self.date)
        form.addRow(QLabel("یادداشت‌های یادآوری:"))
        self.notes = DynamicNotesWidget(); form.addRow(self.notes)
        ok = QPushButton("تأیید", self); ok.clicked.connect(self.on_ok)
        form.addRow(ok)
    def on_ok(self):
        dtxt = self.date.text().strip()
        if not validate_jalali(dtxt):
            QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ شمسی معتبر وارد کنید (YYYY/MM/DD)")
            return
        d = jdatetime.datetime.strptime(dtxt, "%Y/%m/%d").date()
        if d < jdatetime.date.today():
            QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ یادآوری نباید گذشته باشد")
            return
        self.accept()
    def get_data(self):
        return {'next_date': self.date.text().strip(),
                'reminder_notes': self.notes.get_notes(),
                'status': self.status}

class FinalizeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("پرونده مختومه شد")
        form = QFormLayout(self)

        # اجازه فقط رقم و کاما (مثل فیلد مبلغ مالیات)
        regex = QRegularExpression(r'^[\d,]{0,18}$')
        self.final = QLineEdit(self)
        self.final.setValidator(QRegularExpressionValidator(regex, self.final))
        self.final.textEdited.connect(self._on_final_amount_edited)  # فرمت زنده

        form.addRow("مبلغ تعیین شده نهایی:", self.final)

        ok = QPushButton("تأیید", self)
        ok.clicked.connect(self.on_ok)
        form.addRow(ok)

    # --- همان منطق فرمت و نگه‌داشتن کرسر، ساده و خودبسنده ---
    def _format_with_commas(self, value: str) -> str:
        """فقط رقم‌ها را نگه می‌دارد و سه‌رقمی می‌کند؛ خالی را همان خالی برمی‌گرداند."""
        if value == "":
            return ""
        digits = "".join(ch for ch in value if ch.isdigit())
        if digits == "":
            return ""
        digits = digits.lstrip("0") or "0"
        return "{:,}".format(int(digits))

    def _compute_new_cursor_after_format(self, old_text: str, old_cursor: int, new_text: str) -> int:
        """مکان‌نما را طوری می‌گذارد که تعداد رقم‌های قبل از آن حفظ شود."""
        digits_before = sum(1 for ch in old_text[:old_cursor] if ch.isdigit())
        count = 0
        for i, ch in enumerate(new_text):
            if ch.isdigit():
                count += 1
            if count == digits_before:
                return i + 1
        return len(new_text)

    def _on_final_amount_edited(self, _text: str):
        """فرمت زنده برای فیلد مبلغ نهایی"""
        old_text = self.final.text()
        old_cursor = self.final.cursorPosition()

        new_text = self._format_with_commas(old_text)
        if new_text == old_text:
            return

        new_cursor = self._compute_new_cursor_after_format(old_text, old_cursor, new_text)
        self.final.blockSignals(True)
        try:
            self.final.setText(new_text)
            self.final.setCursorPosition(max(0, min(len(new_text), new_cursor)))
        finally:
            self.final.blockSignals(False)

    def on_ok(self):
        if not self.final.text().strip():
            QMessageBox.warning(self, "اجباری", "لطفاً مبلغ نهایی را وارد کنید")
            return
        self.accept()

    def get_data(self):
        # _safe_int_from_text قبلاً کاما و ارقام فارسی/عربی را هندل می‌کند
        _f = _safe_int_from_text(self.final.text())
        return {'final_amount': _f if _f is not None else ''}
class AdjustConfirmDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تعدیل مالیات")
        v = QVBoxLayout(self)
        v.addWidget(QLabel("می‌خواهید پرونده مختومه شود؟", self))
        self.rb_yes = QRadioButton("بله", self); self.rb_no = QRadioButton("خیر", self)
        self.bg = QButtonGroup(self); self.bg.addButton(self.rb_yes); self.bg.addButton(self.rb_no)
        v.addWidget(self.rb_yes); v.addWidget(self.rb_no)
        ok = QPushButton("تأیید", self); ok.clicked.connect(self.on_ok)
        v.addWidget(ok)
    def on_ok(self):
        if not (self.rb_yes.isChecked() or self.rb_no.isChecked()):
            QMessageBox.warning(self, "اجباری", "لطفاً یک گزینه انتخاب کنید")
            return
        self.accept()
    def get_decision(self) -> bool:
        return self.rb_yes.isChecked()

# --------- Sheet fetching helpers (بدون JSON) ---------
def _normalize_header(hs):
    return [str(h or "").strip() for h in hs]

def _parse_maybe_json(val):
    s = str(val or "").strip()
    if not s:
        return ""
    try:
        import json as _json
        v = _json.loads(s)
        return v
    except Exception:
        import re as _re
        parts = [p.strip() for p in _re.split(r"[\r\n]+", s) if p.strip()]
        return parts or s

def fetch_record_from_sheet_by_id(record_id: str, spreadsheet_id: str, sa_json_path: str, sheet_name: str) -> dict | None:
    """خواندن سطر مربوط به id از شیت و بازگرداندن dict ستون→مقدار"""
    from google.oauth2.service_account import Credentials
    import gspread

    kind, _sa_src = _resolve_service_account(sa_json_path)
    if kind == 'file':
        creds = Credentials.from_service_account_file(_sa_src, scopes=[
"https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
        ])
    else:
        creds = Credentials.from_service_account_info(_sa_src, scopes=[
"https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
        ])
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(sheet_name)
    except Exception:
        return None

    header = _normalize_header(ws.row_values(1) or [])
    if not header:
        return None
    lower = [h.lower() for h in header]
    try:
        id_col_idx = lower.index("id")
    except ValueError:
        return None

    id_vals = ws.col_values(id_col_idx + 1)[1:]
    rid = str(record_id or "").strip()
    target_row = None
    for i, v in enumerate(id_vals, start=2):
        if str(v).strip() == rid:
            target_row = i
            break
    if not target_row:
        return None

    row_vals = ws.row_values(target_row) or []
    rec = {}
    for i, h in enumerate(header):
        rec[h] = row_vals[i] if i < len(row_vals) else ""
    rec["id"] = rid

    for key in ("notes","reminder notes","reminder_notes","uploaded_files","petition_uploaded_files"):
        if key in rec:
            rec[key] = _parse_maybe_json(rec[key])
    return rec

# ---- عددخوان امن: ارقام فارسی/عربی، جداکننده‌ها، و نما (E-notation) ----
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
_FA_TO_EN = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
_AR_TO_EN = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def _to_en_digits(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = (s.replace(",", "")
           .replace("٬", "")
           .replace("،", "")
           .replace(" ", "")
           .replace("\\u200f","")
           .replace("\\u200e",""))
    s = s.replace("٫", ".")
    s = s.translate(_FA_TO_EN).translate(_AR_TO_EN)
    return s

def _safe_int_from_text(s: str):
    s = _to_en_digits(s or "")
    if s == "": return None
    try:
        d = Decimal(s)
        d = d.quantize(Decimal(1), rounding=ROUND_HALF_UP)
        return int(d)
    except (InvalidOperation, ValueError):
        return None

# ===================== کلاس اصلی =====================
class EditorWindow(QTabWidget):
    def __init__(self, record_id: str,
                 spreadsheet_id: str | None = None,
                 sa_json_path: str | None = None,
                 sheet_name: str | None = None,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("AbbaspoorPage")
        self._record_id = str(record_id or "").strip()
        # تنظیم پارامترهای شیت (از آرگومان یا از env موجود در همین فایل)
        self._spreadsheet_id = (spreadsheet_id or GOOGLE_SHEETS_KEY).strip()
        self._sa_json_path   = (sa_json_path   or GOOGLE_SA_JSON).strip()
        self._sheet_name     = (sheet_name     or GOOGLE_SHEET_NAME).strip()

        self.setWindowTitle("ویرایش پرونده")
        self.resize(860, 1140)
        self.global_settings = self._load_settings()
        self._init_ui()
        try:
            _apply_readonly_fields(self)
        except Exception:
            pass
        self._load_record_into_form(None)

    # ---------- Helpers ----------
    def _load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with suppress(Exception):
                return json.load(open(SETTINGS_FILE,'r',encoding='utf-8'))
        # اگر نبود، چیزی تحمیل نکنیم
        return {}

    def _is_238_expired(self) -> bool:
        md = self.mad238_agreement_deadline.text().strip()
        if not validate_jalali(md): return False

        try:
            dd = jdatetime.datetime.strptime(md, "%Y/%m/%d").date()
            return dd <= jdatetime.date.today()
        except Exception:
            return False

    def _lock_bodavi_tajdid(self, disable: bool):
        for rb in (self.rb_adjust, self.rb_refer):
            rb.setEnabled(not disable)
            if disable:
                rb.setAutoExclusive(False); rb.setChecked(False); rb.setAutoExclusive(True)
        if disable:
            with suppress(Exception):
                self.bodavi.reset(disable_all=True)
                self.tajdid.reset(disable_all=True)
            self.bodavi.setEnabled(False); self.tajdid.setEnabled(False)

    def _set_combo_by_text(self, combo: QComboBox, text: str):
        try:
            if not combo or not text:
                return
            t = text.strip()
            i = combo.findText(t, Qt.MatchExactly)
            if i >= 0:
                combo.setCurrentIndex(i)
            else:
                if combo.isEditable():
                    combo.setCurrentText(t)
                else:
                    combo.addItem(t)
                    combo.setCurrentIndex(combo.count() - 1)
        except Exception:
            pass

    # ================== UI ==================
    def _init_ui(self):
        tab = QWidget(); tab.setObjectName("AbbaspoorPage")
        self.addTab(tab, "ویرایش پرونده")
        form = QFormLayout(); self.form = form
        self.national_id = QLineEdit()
        self.national_id.setValidator(QRegularExpressionValidator(QRegularExpression(r'\d+'), self.national_id))
        form.addRow("شناسه ملی*:", self.national_id)
        self.archive = QLineEdit()
        # فقط عدد، / و _
        self.archive.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r'[0-9/_-]+'),
                self.archive
            )
        )
        form.addRow("شماره بایگانی*:", self.archive)
        # نام شرکت و سال مالی
        self.company = QLineEdit(); form.addRow("نام شخص/شرکت*:", self.company)
        self.fiscal  = QLineEdit(); self.fiscal.setMaxLength(4); form.addRow("سال مالی*:", self.fiscal)

        # تاریخ ورود
        self.entry = QLineEdit(); self.entry.setInputMask("0000/00/00;_"); form.addRow("تاریخ ورود به موسسه:", self.entry)

        
        # نوع پرونده
        self.case_types = ["تکلیفی","حقوقی","ارزش افزوده","مالیات بر عملکرد","مستقلات"]
        self.case_checkboxes = []
        h_case = QHBoxLayout()
        for label in self.case_types:
            cb = QCheckBox(label)
            self.case_checkboxes.append(cb)
            h_case.addWidget(cb)
        form.addRow("نوع پرونده:", h_case)


        # رفرنس مستقیم برای «ارزش افزوده» و «مالیات بر عملکرد»
        try:
            self.cb_vat = self.case_checkboxes[self.case_types.index("ارزش افزوده")]
        except ValueError:
            self.cb_vat = None
        try:
            self.cb_perf = self.case_checkboxes[self.case_types.index("مالیات بر عملکرد")]
        except ValueError:
            self.cb_perf = None

        # هر تغییری در نوع پرونده، وضعیت فیلدهای مالیات/جریمه را آپدیت کند
        for cb in self.case_checkboxes:
            cb.toggled.connect(self._on_case_type_changed)

        # Backward-compat shim for legacy code expecting self.group_case (QButtonGroup)
        class _DummyGroupCase:
            def __init__(self, boxes): self._boxes = boxes
            def buttons(self): return list(self._boxes)
        self.group_case = _DummyGroupCase(self.case_checkboxes)



        # ارائه اسناد
        self.submit_date = QLineEdit(); self.submit_date.setInputMask("0000/00/00;_")
        form.addRow("تاریخ ارائه اسناد و مدارک:", self.submit_date)
        self.deadline_days = QSpinBox(); self.deadline_days.setRange(0,365)
        form.addRow("چند روز مهلت برای ارائه هست:", self.deadline_days)
        self.due_date = QLineEdit(); self.due_date.setReadOnly(True)
        form.addRow("مهلت ارائه اسناد و مدارک:", self.due_date)
        self.submit_date.textChanged.connect(self._update_due)
        self.deadline_days.valueChanged.connect(self._update_due)

        # وضعیت ارائه اسناد
        self.status_texts = ["ارائه شد","ارائه نشد"]
        self.group_status = QButtonGroup(self)
        h_status = QHBoxLayout()
        for idx, text in enumerate(self.status_texts):
            rb = QRadioButton(text)
            self.group_status.addButton(rb, idx)
            h_status.addWidget(rb)
        form.addRow("وضعیت ارائه اسناد:", h_status)

        # آپلود مدارک
        self.upload_date = QLineEdit(); self.upload_date.setInputMask("0000/00/00;_"); self.upload_date.setEnabled(False)
        form.addRow("تاریخ ارائه مدارک:", self.upload_date)
        self.upload_btn = QPushButton("آپلود فایل‌ها"); self.upload_btn.setEnabled(False)
        self.upload_btn.clicked.connect(self._upload_files); form.addRow(self.upload_btn)
        self.upload_list = QListWidget(); form.addRow(QLabel("فایل‌های آپلود شده:"), self.upload_list)
        self.uploaded_files: List[str] = []

        # برگه تشخیص؟
        self.rb_has_ass_yes = QRadioButton("بله")
        self.rb_has_ass_no  = QRadioButton("خیر")
        self.group_has_ass = QButtonGroup(self); self.group_has_ass.addButton(self.rb_has_ass_yes, 1); self.group_has_ass.addButton(self.rb_has_ass_no, 0)
        h_ass = QHBoxLayout(); h_ass.addWidget(self.rb_has_ass_yes); h_ass.addWidget(self.rb_has_ass_no)
        form.addRow("برگه تشخیص دارد؟", h_ass)
        for rb in (self.rb_has_ass_yes, self.rb_has_ass_no): rb.setEnabled(False)

        # فیلدهای دوره‌ای مخصوص «ارزش افزوده» (۴ دوره، هرکدام: مبلغ مالیات + مبلغ جریمه)
        self.vat_period_rows = []
        for i in range(1, 5):
            row_w = QWidget()
            h = QHBoxLayout(row_w)
            h.setContentsMargins(0, 0, 0, 0)

            tax_edit = QLineEdit()
            tax_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r'^[\d,]{0,18}$'), tax_edit))
            tax_edit.textEdited.connect(self._on_penalty_amount_edited)
            tax_edit.setEnabled(False)

            pen_edit = QLineEdit()
            pen_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r'^[\d,]{0,18}$'), pen_edit))
            pen_edit.textEdited.connect(self._on_penalty_amount_edited)
            pen_edit.setEnabled(False)

            h.addWidget(QLabel("مبلغ مالیات:"))
            h.addWidget(tax_edit)
            h.addWidget(QLabel("مبلغ جریمه:"))
            h.addWidget(pen_edit)

            row_w.setVisible(False)
            self.vat_period_rows.append((row_w, tax_edit, pen_edit))
            form.addRow(f"دوره {i}:", row_w)

        # مبلغ مالیات کلی
        self.penalty_amount = QLineEdit()
        self.penalty_amount.setValidator(QRegularExpressionValidator(QRegularExpression(r'^[\d,]{0,18}$'), self.penalty_amount))
        self.penalty_amount.textEdited.connect(self._on_penalty_amount_edited)
        self.penalty_amount.setEnabled(False)
        form.addRow("مبلغ مالیات:", self.penalty_amount)

        # فیلد «جریمه» مخصوص پرونده‌های «مالیات بر عملکرد»
        self.performance_penalty = QLineEdit()
        self.performance_penalty.setValidator(QRegularExpressionValidator(QRegularExpression(r'^[\d,]{0,18}$'), self.performance_penalty))
        self.performance_penalty.textEdited.connect(self._on_penalty_amount_edited)
        self.performance_penalty.setEnabled(False)
        self.performance_penalty.setVisible(False)
        form.addRow("جریمه:", self.performance_penalty)

# تاریخ صدور برگه تشخیص و مهلت اعتراض 30روزه
        self.assess_date = QLineEdit(); self.assess_date.setInputMask("0000/00/00;_"); self.assess_date.setEnabled(False)
        form.addRow("تاریخ ابلاغ برگه تشخیص:", self.assess_date)
        self.assess_deadline = QLineEdit(); self.assess_deadline.setReadOnly(True); self.assess_deadline.setEnabled(False)
        form.addRow("مهلت اعتراض برگه تشخیص:", self.assess_deadline)
        self.assess_date.textChanged.connect(self._update_assess_deadline)

        # گزارش/اعتراض
        self.rb_report_yes = QRadioButton("بله")
        self.rb_report_no  = QRadioButton("خیر")
        self.group_report = QButtonGroup(self); self.group_report.addButton(self.rb_report_yes, 1); self.group_report.addButton(self.rb_report_no, 0)
        h_rep = QHBoxLayout(); h_rep.addWidget(self.rb_report_yes); h_rep.addWidget(self.rb_report_no)
        form.addRow("گزارش رسیدگی دارد؟", h_rep)
        for rb in (self.rb_report_yes, self.rb_report_no): rb.setEnabled(False)
        # آپلود فایل‌های گزارش رسیدگی
        self.report_upload_btn = QPushButton("آپلود فایل‌های گزارش رسیدگی")
        self.report_upload_btn.setEnabled(False)
        self.report_upload_btn.clicked.connect(self._upload_report_files)
        form.addRow(self.report_upload_btn)

        self.report_upload_list = QListWidget()
        form.addRow(QLabel("فایل‌های گزارش رسیدگی:"), self.report_upload_list)
        self.report_uploaded_files: List[str] = []
        self.rb_objected_yes = QRadioButton("بله")
        self.rb_objected_no  = QRadioButton("خیر")
        self.group_objected = QButtonGroup(self); self.group_objected.addButton(self.rb_objected_yes, 1); self.group_objected.addButton(self.rb_objected_no, 0)
        h_obj = QHBoxLayout(); h_obj.addWidget(self.rb_objected_yes); h_obj.addWidget(self.rb_objected_no)
        form.addRow("اعتراض شده؟", h_obj)
        for rb in (self.rb_objected_yes, self.rb_objected_no): rb.setEnabled(False)

        # تاریخ اعتراض + لایحه
        self.appeal_send = QLineEdit(); self.appeal_send.setInputMask("0000/00/00;_"); self.appeal_send.setEnabled(False)
        form.addRow("تاریخ اعتراض:", self.appeal_send)
        self.petition_upload_btn = QPushButton("آپلود فایل‌های لایحه"); self.petition_upload_btn.setEnabled(False)
        self.petition_upload_btn.clicked.connect(self._upload_petition_files); form.addRow(self.petition_upload_btn)
        self.petition_upload_list = QListWidget(); form.addRow(QLabel("فایل‌های لایحه:"), self.petition_upload_list)
        self.petition_uploaded_files: List[str] = []

        # ماده ۲۳۸
        self.mad238_entry_date = QLineEdit(); self.mad238_entry_date.setInputMask("0000/00/00;_"); self.mad238_entry_date.setEnabled(False)
        form.addRow("تاریخ ورود به ماده ۲۳۸:", self.mad238_entry_date)
        self.mad238_agreement_deadline = QLineEdit(); self.mad238_agreement_deadline.setReadOnly(True); self.mad238_agreement_deadline.setEnabled(False)
        form.addRow("مهلت توافق ماده ۲۳۸:", self.mad238_agreement_deadline)
        self.mad238_entry_date.textChanged.connect(self._update_mad238_agreement_deadline)

        # نتیجه توافق
        self.rb_adjust = QRadioButton("تعدیل مالیات")
        self.rb_refer  = QRadioButton("ارجاع به هیأت بدوی")
        self.result_bg = QButtonGroup(self)
        for rb in (self.rb_adjust, self.rb_refer):
            self.result_bg.addButton(rb); rb.setEnabled(False); rb.toggled.connect(self._mark_dirty)
        h_res = QHBoxLayout(); h_res.addWidget(self.rb_adjust); h_res.addWidget(self.rb_refer)
        grp = QGroupBox("نتیجه توافق"); grp.setLayout(h_res); form.addRow(grp)

        # پنل بدوی/تجدیدنظر
        self.bodavi = BodaviPanel(); self.bodavi.setEnabled(False); form.addRow(self.bodavi)
        self.tajdid = TajdidPanel(); self.tajdid.setEnabled(False); form.addRow(self.tajdid)
        self.rb_refer.toggled.connect(self._on_refer_toggled)
        # اتصال هر دو دکمه اعتراض بدوی
        try:
            self.bodavi.obj_yes.toggled.connect(self._on_bodavi_obj_yes_toggled)
            self.bodavi.obj_no.toggled.connect(self._on_bodavi_obj_no_toggled)
        except Exception:
            pass

        # یادداشت‌ها
        form.addRow(QLabel("یادداشت‌های پرونده:"))
        self.notes_w = DynamicNotesWidget(); form.addRow(self.notes_w)

        # دکمه ذخیره (ویرایش)
        self.btn_save = QPushButton("ذخیرهٔ ویرایش"); self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save)
        form.addRow(self.btn_save)

        # اسکرول + نوار وضعیت
        container = QFrame(); container.setObjectName("AbbaspoorFrame"); container.setLayout(form)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(container)
        self.status_lbl = QLabel("حالت ویرایش")

        tab_layout = QVBoxLayout()
        tab_layout.addWidget(scroll)
        tab_layout.addWidget(self.status_lbl)
        tab.setLayout(tab_layout)

        # اتصالات تکمیلی
        self.group_status.buttonClicked.connect(lambda btn: self._on_status_changed(self.group_status.id(btn)))
        self.group_has_ass.buttonClicked.connect(lambda btn: self._on_assessment_changed(self.group_has_ass.id(btn)))
        self.group_report.buttonClicked.connect(lambda btn: self._on_report_changed(self.group_report.id(btn)))
        self.group_objected.buttonClicked.connect(lambda btn: self._on_objected_changed(self.group_objected.id(btn)))
        self.appeal_send.textChanged.connect(self._on_appeal_send_change)

        # Watchers
        self._wire_dirty_watchers()

    # ───── رویدادها ─────
    def _format_with_commas(self, value: str) -> str:
        """فقط رقم‌ها را نگه می‌دارد و سه‌رقمی می‌کند؛ خالی را همان خالی برمی‌گرداند."""
        if value == "":
            return ""
        # حذف همه چیز به جز رقم
        digits = "".join(ch for ch in value if ch.isdigit())
        if digits == "":
            return ""
        # حذف صفرهای اضافه‌ی ابتدای عدد (به جز اینکه کل عدد صفر باشد)
        digits = digits.lstrip("0") or "0"
        return "{:,}".format(int(digits))

    def _compute_new_cursor_after_format(self, old_text: str, old_cursor: int, new_text: str) -> int:
        """نشانگر را طوری تنظیم می‌کند که همان تعداد رقم قبل از آن حفظ شود."""
        # تعداد رقم‌های قبل از نشانگر در متن قدیمی
        digits_before = sum(1 for ch in old_text[:old_cursor] if ch.isdigit())
        # روی متن جدید جلو می‌رویم تا همان تعداد رقم را رد کنیم
        count = 0
        for i, ch in enumerate(new_text):
            if ch.isdigit():
                count += 1
            if count == digits_before:
                return i + 1
        return len(new_text)

    def _on_penalty_amount_edited(self, _text: str):
        """هندلر فرمت زنده برای QLineEdit مبلغ مالیات"""
        # متن و مکان‌نما قبل از اعمال فرمت
        old_text = self.penalty_amount.text()
        old_cursor = self.penalty_amount.cursorPosition()

        new_text = self._format_with_commas(old_text)
        if new_text == old_text:
            return

        new_cursor = self._compute_new_cursor_after_format(old_text, old_cursor, new_text)
        self.penalty_amount.blockSignals(True)   # از لوپ جلوگیری شود
        try:
            self.penalty_amount.setText(new_text)
            # محدود کردن ایندکس به بازه معتبر
            new_cursor = max(0, min(len(new_text), new_cursor))
            self.penalty_amount.setCursorPosition(new_cursor)
        finally:
            self.penalty_amount.blockSignals(False)
    def _update_due(self):
        txt = self.submit_date.text().strip()
        if not validate_jalali(txt):
            self.due_date.clear(); return
        d = jdatetime.datetime.strptime(txt, "%Y/%m/%d")
        dd = d + jdatetime.timedelta(days=self.deadline_days.value())
        self.due_date.setText(dd.strftime("%Y/%m/%d"))

    def _on_status_changed(self, id):
        for bg in (self.group_has_ass, self.group_report, self.group_objected):
            bg.setExclusive(False)
            for btn in bg.buttons(): btn.setChecked(False)
            bg.setExclusive(True)
        upload_ok = (id == 0)
        if not upload_ok:
            self.upload_date.clear(); self.upload_date.setEnabled(False)
            self.upload_list.clear(); self.uploaded_files = []; self.upload_btn.setEnabled(False)
        else:
            self.upload_date.setEnabled(True); self.upload_btn.setEnabled(True)
        for rb in (self.rb_has_ass_yes, self.rb_has_ass_no): rb.setEnabled(True)
        self._mark_dirty()

    
    def _on_assessment_changed(self, id):
        has_ass = (id == 1)
        self.result_bg.setExclusive(False)
        for btn in self.result_bg.buttons():
            btn.setChecked(False)
            btn.setEnabled(False)
        self.result_bg.setExclusive(True)

        if has_ass:
            self.assess_date.setEnabled(True)
            self.assess_deadline.setEnabled(True)
            for rb in (self.rb_report_yes, self.rb_report_no,
                       self.rb_objected_yes, self.rb_objected_no):
                rb.setEnabled(True)
        else:
            for bg in (self.group_report, self.group_objected):
                bg.setExclusive(False)
                for btn in bg.buttons():
                    btn.setChecked(False)
                    btn.setEnabled(False)
                bg.setExclusive(True)

            self.assess_date.clear()
            self.assess_date.setEnabled(False)
            self.assess_deadline.clear()
            self.assess_deadline.setEnabled(False)
            self.appeal_send.clear()
            self.appeal_send.setEnabled(False)
            self.petition_upload_btn.setEnabled(False)
            self.petition_upload_list.clear()
            self.petition_uploaded_files = []
            self.mad238_entry_date.clear()
            self.mad238_entry_date.setEnabled(False)
            self.mad238_agreement_deadline.clear()
            self.mad238_agreement_deadline.setEnabled(False)
            self.report_upload_btn.setEnabled(False)
            self.report_upload_list.clear()
            self.report_uploaded_files = []
            self.penalty_amount.clear()
            self.penalty_amount.setEnabled(False)
            if hasattr(self, "performance_penalty"):
                self.performance_penalty.clear()
                self.performance_penalty.setEnabled(False)
            if hasattr(self, "vat_period_rows"):
                for row_w, tax_edit, pen_edit in self.vat_period_rows:
                    tax_edit.clear()
                    pen_edit.clear()
                    tax_edit.setEnabled(False)
                    pen_edit.setEnabled(False)

        # وضعیت فیلدهای وابسته به نوع پرونده را همگام کن
        try:
            self._update_case_dependent_fields()
        except Exception:
            pass

        self._mark_dirty()

    def _update_assess_deadline(self):
        txt = self.assess_date.text().strip()
        if not validate_jalali(txt):
            self.assess_deadline.clear(); return
        d = jdatetime.datetime.strptime(txt, "%Y/%m/%d")
        dd = d + jdatetime.timedelta(days=30)
        self.assess_deadline.setText(dd.strftime("%Y/%m/%d"))


    def _on_case_type_changed(self, _checked: bool):
        """هر تغییری در نوع پرونده، وضعیت فیلدهای مالیات/جریمه را آپدیت می‌کند."""
        try:
            self._update_case_dependent_fields()
        except Exception:
            pass
        self._mark_dirty()

    def _update_case_dependent_fields(self):
        """نمایش/فعال‌سازی فیلدهای مبلغ مالیات و جریمه‌ها بر اساس نوع پرونده و برگه تشخیص."""
        has_ass = (self.group_has_ass.checkedId() == 1) if hasattr(self, "group_has_ass") else False

        selected_cases = [
            cb.text()
            for cb in getattr(self, "case_checkboxes", [])
            if cb.isChecked()
        ]

        is_vat = ("ارزش افزوده" in selected_cases)
        is_perf = ("مالیات بر عملکرد" in selected_cases)
        only_vat = (is_vat and len(selected_cases) == 1)

        # مبلغ مالیات کلی
        if only_vat:
            self.penalty_amount.clear()
            self.penalty_amount.setEnabled(False)
        else:
            self.penalty_amount.setEnabled(bool(has_ass and selected_cases))

        # جریمه مخصوص «مالیات بر عملکرد»
        if hasattr(self, "performance_penalty"):
            self.performance_penalty.setVisible(is_perf)
            self.performance_penalty.setEnabled(is_perf and has_ass)
            if not is_perf:
                self.performance_penalty.clear()

        # دوره‌های ارزش افزوده
        if hasattr(self, "vat_period_rows"):
            for row_w, tax_edit, pen_edit in self.vat_period_rows:
                row_w.setVisible(is_vat)
                tax_edit.setEnabled(is_vat and has_ass)
                pen_edit.setEnabled(is_vat and has_ass)
                if not is_vat:
                    tax_edit.clear()
                    pen_edit.clear()

    def _on_report_changed(self, id):
        has_rep = (id == 1)
        if has_rep:
            self.report_upload_btn.setEnabled(True)
        else:
            self.report_upload_btn.setEnabled(False)
            self.report_upload_list.clear()
            self.report_uploaded_files = []
        self._mark_dirty()
    def _on_objected_changed(self, id):
        is_obj = (id == 1)
        if is_obj:
            self.appeal_send.setEnabled(True); self.petition_upload_btn.setEnabled(True)
            self.mad238_entry_date.clear();   self.mad238_entry_date.setEnabled(False)
            self.mad238_agreement_deadline.clear(); self.mad238_agreement_deadline.setEnabled(False)
        else:
            self.appeal_send.clear(); self.appeal_send.setEnabled(False)
            self.petition_upload_btn.setEnabled(False)
            self.petition_upload_list.clear(); self.petition_uploaded_files = []
            self.mad238_entry_date.setEnabled(True)
            self._update_mad238_agreement_deadline()
        self._mark_dirty()

    def _on_appeal_send_change(self, text):
        txt = text.strip()
        ok = validate_jalali(txt)

        # فقط اگر تاریخ درست بود و "اعتراض شده" = بله بود
        if ok and self.group_objected.checkedId() == 1:
            # کپی تاریخ اعتراض تو تاریخ ورود به ماده ۲۳۸
            self.mad238_entry_date.setText(txt)
            self.mad238_entry_date.setEnabled(True)

            # محاسبه مهلت توافق ماده ۲۳۸
            self._update_mad238_agreement_deadline()
        else:
            # اگر تاریخ نامعتبر شد یا اصلاً اعتراض نشده
            self.mad238_entry_date.clear()
            self.mad238_entry_date.setEnabled(False)
            self.mad238_agreement_deadline.clear()
            for rb in (self.rb_adjust, self.rb_refer):
                rb.setEnabled(False)
                rb.setAutoExclusive(False); rb.setChecked(False); rb.setAutoExclusive(True)
        self._mark_dirty()

    def _update_mad238_agreement_deadline(self):
        txt = self.mad238_entry_date.text().strip()
        if not validate_jalali(txt):
            self.mad238_agreement_deadline.clear()
            self._lock_bodavi_tajdid(disable=True)
            return
        d = jdatetime.datetime.strptime(txt, "%Y/%m/%d")
        dd = d + jdatetime.timedelta(days=45)
        self.mad238_agreement_deadline.setText(dd.strftime("%Y/%m/%d"))
        # مهم: نتیجه توافق را بدون توجه به گذشته/نگذشته بودن تاریخ باز کن
        self._lock_bodavi_tajdid(disable=False)
        self._mark_dirty()

    def _on_refer_toggled(self, checked: bool):

        self.bodavi.setEnabled(checked)
        if checked:
            if hasattr(self.bodavi, "start"): self.bodavi.start()
            self.tajdid.setEnabled(False); self.tajdid.reset(disable_all=True)
        else:
            self.bodavi.reset(disable_all=True); self.tajdid.reset(disable_all=True); self.tajdid.setEnabled(False)
        self._mark_dirty()

    def _on_bodavi_obj_yes_toggled(self, checked: bool):
        if checked:
            if hasattr(self.tajdid, "reset"): self.tajdid.reset(disable_all=False)
            self.tajdid.setEnabled(True)
            if hasattr(self.tajdid, "start"): self.tajdid.start()
            if hasattr(self.tajdid, "refer_date"):
                self.tajdid.refer_date.setEnabled(True); self.tajdid.refer_date.setFocus()
        self._mark_dirty()

    def _on_bodavi_obj_no_toggled(self, checked: bool):
        if checked:
            if hasattr(self.tajdid, "reset"): self.tajdid.reset(disable_all=True)
            self.tajdid.setEnabled(False)
        self._mark_dirty()

    # ====== فایل‌ها ======
    def _file_md5(self, p: str) -> str:
        import hashlib
        h = hashlib.md5()
        with open(p, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()

    def _dedup_against_current(self, src_abs: str, current_rel_list: list) -> bool:
        try:
            src_md5 = self._file_md5(src_abs)
        except Exception:
            return False
        for rel in current_rel_list:
            dest_abs = os.path.abspath(os.path.join(PROJECT_ROOT, rel))
            if os.path.isfile(dest_abs):
                with suppress(Exception):
                    if self._file_md5(dest_abs) == src_md5:
                        return True
        return False

    def _upload_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "انتخاب فایل‌ها", "", "فایل‌های مجاز (*.png *.jpg *.jpeg *.pdf *.txt *.docx *.doc *.xlsx)")
        if not files:
            QMessageBox.information(self, "", "هیچ فایلی انتخاب نشد"); return
        new_any = False
        for src in files:
            src_abs = os.path.abspath(src)
            if self._dedup_against_current(src_abs, self.uploaded_files): continue
            name  = os.path.basename(src)
            stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            dest  = os.path.join(UPLOAD_ROOT, f"{os.path.splitext(name)[0]}_{stamp}{os.path.splitext(name)[1]}")
            shutil.copy2(src, dest)
            try:
                rel = os.path.relpath(dest, PROJECT_ROOT)
            except ValueError:
                # اگر روی درایو دیگه بود (مثل Z در مقابل C)، همون مسیر کامل رو نگه دار
                rel = dest
            self.uploaded_files.append(rel)
            self.upload_list.addItem(QListWidgetItem(os.path.basename(dest)))
            new_any = True
        if not new_any:
            QMessageBox.information(self, "", "فایل تکراری انتخاب شد؛ چیزی اضافه نشد.")
        self._mark_dirty()

    def _upload_petition_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "انتخاب فایل‌های لایحه", "", "فایل‌های مجاز (*.png *.jpg *.jpeg *.pdf *.txt *.docx *.doc *.xlsx)")
        if not files:
            QMessageBox.information(self, "", "هیچ فایلی انتخاب نشد"); return
        new_any = False
        for src in files:
            src_abs = os.path.abspath(src)
            if self._dedup_against_current(src_abs, self.petition_uploaded_files): continue
            name  = os.path.basename(src)
            stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            dest  = os.path.join(UPLOAD_ROOT, f"{os.path.splitext(name)[0]}_{stamp}{os.path.splitext(name)[1]}")
            shutil.copy2(src, dest)
            try:
                rel = os.path.relpath(dest, PROJECT_ROOT)
            except ValueError:
                rel = dest
            self.petition_uploaded_files.append(rel)
            self.petition_upload_list.addItem(QListWidgetItem(os.path.basename(dest)))
            new_any = True
        if not new_any:
            QMessageBox.information(self, "", "فایل تکراری انتخاب شد؛ چیزی اضافه نشد.")
        self._mark_dirty()
    def _upload_report_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "انتخاب فایل‌های لایحه", "", "فایل‌های مجاز (*.png *.jpg *.jpeg *.pdf *.txt *.docx *.doc *.xlsx)")
        if not files:
            QMessageBox.information(self, "", "هیچ فایلی انتخاب نشد"); return
        new_any = False
        for src in files:
            src_abs = os.path.abspath(src)
            if self._dedup_against_current(src_abs, self.report_uploaded_files): continue
            name  = os.path.basename(src)
            stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            dest  = os.path.join(UPLOAD_ROOT, f"{os.path.splitext(name)[0]}_{stamp}{os.path.splitext(name)[1]}")
            shutil.copy2(src, dest)
            try:
                rel = os.path.relpath(dest, PROJECT_ROOT)
            except ValueError:
                rel = dest
            self.report_uploaded_files.append(rel)
            self.report_upload_list.addItem(QListWidgetItem(os.path.basename(dest)))
            new_any = True
        if not new_any:
            QMessageBox.information(self, "", "فایل تکراری انتخاب شد؛ چیزی اضافه نشد.")
        self._mark_dirty()
    # ---------- Dirty Watchers ----------
    def _snapshot_panels(self) -> Dict[str, Any]:
        """مینیمال اسنپ‌شات از پنل‌های بدوی/تجدیدنظر برای تشخیص تغییرات."""
        def _txt(w):
            try:
                return w.text().strip()
            except Exception:
                return ""
        def _rb_pair(yes, no):
            try:
                if hasattr(yes, "isChecked") and yes.isChecked(): return "بله"
                if hasattr(no, "isChecked") and no.isChecked():   return "خیر"
            except Exception:
                pass
            return ""
        def _cmb(w):
            try:
                return w.currentText().strip()
            except Exception:
                return ""
        bodavi_min = {}
        try:
            b = self.bodavi
            bodavi_min = {
                'bodavi_session_date': _txt(getattr(b, 'session_date', getattr(b, 'refer_date', ""))),
                'bodavi_verdict_date': _txt(getattr(b, 'verdict_date', "")),
                'bodavi_appeal_deadline': _txt(getattr(b, 'appeal_deadline', getattr(b, 'objection_deadline', ""))),
                'bodavi_appeal_done': _rb_pair(getattr(b, 'obj_yes', None), getattr(b, 'obj_no', None)),
                'bodavi_appeal_date': _txt(getattr(b, 'appeal_date', getattr(b, 'objection_date', ""))),
                'bodavi_verdict': _cmb(getattr(b, 'verdict', None)) if hasattr(getattr(b, 'verdict', None), 'currentText') else (
                                   'تایید' if getattr(getattr(b, 'v_approve', None), 'isChecked', lambda: False)() else (
                                   'تعدیل' if getattr(getattr(b, 'v_adjust', None), 'isChecked', lambda: False)() else "")),
                'needs_investigation': ("TRUE" if getattr(getattr(b, 'needs_investigation', None), 'isChecked', lambda: False)() else (
                                        "بله" if getattr(getattr(b, 'invest_yes', None), 'isChecked', lambda: False)() else (
                                        "خیر" if getattr(getattr(b, 'invest_no', None), 'isChecked', lambda: False)() else ""))),
            }
        except Exception:
            pass
        tajdid_min = {}
        try:
            t = self.tajdid
            tajdid_min = {
                'tajdid_refer_date': _txt(getattr(t, 'refer_date', "")),
                'verdict_date_tajdid': _txt(getattr(t, 'verdict_date', "")),
                'objection_deadline_tajdid': _txt(getattr(t, 'objection_deadline', "")),
                'objection_done_tajdid': _rb_pair(getattr(t, 'obj_yes', None), getattr(t, 'obj_no', None)),
                'objection_date_tajdid': _txt(getattr(t, 'objection_date', "")),
                'verdict_result_tajdid': _cmb(getattr(t, 'verdict_result', None)),
                'verification_status': _cmb(getattr(t, 'verification_status', None)),
                'council_date': _txt(getattr(t, 'council_date', "")),
                'needs_investigation_tajdid': ("TRUE" if getattr(getattr(t, 'needs_investigation', None), 'isChecked', lambda: False)() else ""),
                'final_amount': _txt(getattr(t, 'final_amount', "")),
            }
        except Exception:
            pass
        return {**bodavi_min, **tajdid_min}

    
    def _snapshot_current_form(self) -> Dict[str, Any]:

        case_list = [cb.text() for cb in getattr(self, 'case_checkboxes', []) if getattr(cb, 'isChecked', lambda: False)()]
        case = "، ".join(case_list)

        status = ""
        for btn in self.group_status.buttons():
            if btn.isChecked():
                status = btn.text()
                break

        has_ass = "" if self.group_has_ass.checkedId() < 0 else ("بله" if self.group_has_ass.checkedId() == 1 else "خیر")
        report  = "" if self.group_report.checkedId()   < 0 else ("بله" if self.group_report.checkedId()   == 1 else "خیر")
        obj     = "" if self.group_objected.checkedId() < 0 else ("بله" if self.group_objected.checkedId() == 1 else "خیر")

        if self.rb_adjust.isChecked():
            mad238_res = "تعدیل مالیات"
        elif self.rb_refer.isChecked():
            mad238_res = "ارجاع به هیأت بدوی"
        else:
            mad238_res = ""

        jarime_amount = self.penalty_amount.text().strip()
        performance_penalty = self.performance_penalty.text().strip() if hasattr(self, "performance_penalty") else ""

        vat_fields: Dict[str, Any] = {}
        if hasattr(self, "vat_period_rows"):
            for idx, (_row_w, tax_edit, pen_edit) in enumerate(self.vat_period_rows, start=1):
                vat_fields[f"vat_p{idx}_tax"] = tax_edit.text().strip()
                vat_fields[f"vat_p{idx}_penalty"] = pen_edit.text().strip()
        else:
            for idx in range(1, 5):
                vat_fields[f"vat_p{idx}_tax"] = ""
                vat_fields[f"vat_p{idx}_penalty"] = ""

        base = {
            'national_id': self.national_id.text().strip(),
            'archive': self.archive.text().strip(),
            'company_name': self.company.text().strip(),
            'fiscal_year': self.fiscal.text().strip(),
            'entry_date': self.entry.text().strip(),
            'case_type': case,
            'submit_date': self.submit_date.text().strip(),
            'deadline_days': self.deadline_days.value(),
            'due_date': self.due_date.text().strip(),
            'submit_status': status,
            'upload_date': self.upload_date.text().strip(),
            'uploaded_files': list(self.uploaded_files),
            'has_assessment': has_ass,
            'assessment_date': self.assess_date.text().strip(),
            'assessment_deadline': self.assess_deadline.text().strip(),
            'report_exists': report,
            'report_uploaded_files': list(self.report_uploaded_files),
            'objected': obj,
            'appeal_send_date': self.appeal_send.text().strip(),
            'petition_uploaded_files': list(self.petition_uploaded_files),
            'mad238_entry_date': self.mad238_entry_date.text().strip(),
            'mad238_agreement_deadline': self.mad238_agreement_deadline.text().strip(),
            'jarime_amount': jarime_amount,
            'performance_penalty': performance_penalty,
            'vat_p1_tax': vat_fields.get('vat_p1_tax', ''),
            'vat_p1_penalty': vat_fields.get('vat_p1_penalty', ''),
            'vat_p2_tax': vat_fields.get('vat_p2_tax', ''),
            'vat_p2_penalty': vat_fields.get('vat_p2_penalty', ''),
            'vat_p3_tax': vat_fields.get('vat_p3_tax', ''),
            'vat_p3_penalty': vat_fields.get('vat_p3_penalty', ''),
            'vat_p4_tax': vat_fields.get('vat_p4_tax', ''),
            'vat_p4_penalty': vat_fields.get('vat_p4_penalty', ''),
            'notes': self.notes_w.get_notes(),
            'mad238_result': mad238_res,
        }
        base.update(self._snapshot_panels())
        return base



    def _snapshot_full_row(self) -> Dict[str, Any]:
        """تمام فیلدهای هدر را می‌سازد تا سطر شیت دقیقاً بازنویسی شود."""
        base = self._snapshot_current_form()

        # --- بدوی ---
        def _txt(w):
            try: return w.text().strip()
            except Exception: return ""
        # Radio pair helper for Persian yes/no
        def _rb_pair(yes, no):
            try:
                if hasattr(yes, "isChecked") and yes.isChecked(): return "بله"
                if hasattr(no, "isChecked") and no.isChecked(): return "خیر"
            except Exception:
                pass
            return ""

        bodavi = {
            'bodavi_session_date': _txt(getattr(self.bodavi, 'session_date', "")),
            'bodavi_verdict_date': _txt(getattr(self.bodavi, 'verdict_date', "")),
            'bodavi_appeal_deadline': _txt(getattr(self.bodavi, 'appeal_deadline', "")),
            'bodavi_appeal_done': _rb_pair(getattr(self.bodavi, 'obj_yes', None), getattr(self.bodavi, 'obj_no', None)),
            'bodavi_appeal_date': _txt(getattr(self.bodavi, 'appeal_date', "")),
            'bodavi_verdict': getattr(getattr(self.bodavi, 'verdict', None), 'currentText', lambda: "")(),
            'needs_investigation': ("TRUE" if getattr(getattr(self.bodavi, 'needs_investigation', None), 'isChecked', lambda: False)() else ""),
        }

        # --- تجدیدنظر ---
        tajdid = {
            'tajdid_refer_date': _txt(getattr(self.tajdid, 'refer_date', "")),
            'verdict_date_tajdid': _txt(getattr(self.tajdid, 'verdict_date', "")),
            'objection_deadline_tajdid': _txt(getattr(self.tajdid, 'objection_deadline', "")),
            'objection_done_tajdid': _rb_pair(getattr(self.tajdid, 'obj_yes', None), getattr(self.tajdid, 'obj_no', None)),
            'objection_date_tajdid': _txt(getattr(self.tajdid, 'objection_date', "")),
            'verdict_result_tajdid': getattr(getattr(self.tajdid, 'verdict_result', None), 'currentText', lambda: "")(),
            'verification_status': getattr(getattr(self.tajdid, 'verification_status', None), 'currentText', lambda: "")(),
            'council_date': _txt(getattr(self.tajdid, 'council_date', "")),
            'needs_investigation_tajdid': ("TRUE" if getattr(getattr(self.tajdid, 'needs_investigation', None), 'isChecked', lambda: False)() else ""),
            'final_amount': _txt(getattr(self.tajdid, 'final_amount', "")),
        }

        # فیلدهای خارج از فرم: اگر قبلاً مقدار داشتند حفظشان کنیم
        extra_keep = {}
        for k in ("notify_days", "notify_mode"):
            extra_keep[k] = str(getattr(self, "_original_record", {}).get(k, "")).strip()

        # جمع‌بندی
        full = {h: "" for h in DEFAULT_HEADER}
        full.update({k: base.get(k, "") for k in base})
        full.update(bodavi)
        full.update(tajdid)
        full.update(extra_keep)

        # کلیدهای سیستم
        full["status"] = getattr(self, "_status_override", full.get("status",""))
        full["last_action_date"] = full.get("last_action_date", "")
        full["reminder_notes"] = full.get("reminder_notes", [])

        # اگر نتیجه توافق «تعدیل مالیات» شد، کل فیلدهای بدوی/تجدیدنظر پاک شوند
        if full.get("mad238_result") == "تعدیل مالیات":
            for k in ("bodavi_session_date","bodavi_verdict_date","bodavi_appeal_deadline","bodavi_appeal_done",
                      "bodavi_appeal_date","bodavi_verdict","needs_investigation",
                      "tajdid_refer_date","verdict_date_tajdid","objection_deadline_tajdid","objection_done_tajdid",
                      "objection_date_tajdid","verdict_result_tajdid","verification_status","council_date",
                      "needs_investigation_tajdid","final_amount"):
                full[k] = ""

        return full

    def _mark_dirty(self):
        cur = json.dumps(self._snapshot_current_form(), ensure_ascii=False, sort_keys=True)
        self.btn_save.setEnabled(cur != getattr(self, "_orig_snapshot", ""))

    def _wire_panel_dirty_watchers(self, parent):
        if not parent:
            return
        collected = []
        for tp in (
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QRadioButton, QCheckBox,
            QDateEdit, QDateTimeEdit, QTextEdit, QPlainTextEdit
        ):
            try:
                collected.extend(parent.findChildren(tp))
            except Exception:
                pass

        for w in collected:
            try:
                if isinstance(w, QLineEdit):
                    w.textChanged.connect(self._mark_dirty)
                elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
                    w.valueChanged.connect(self._mark_dirty)
                elif isinstance(w, QComboBox):
                    w.currentIndexChanged.connect(self._mark_dirty)
                elif isinstance(w, (QRadioButton, QCheckBox)):
                    w.toggled.connect(self._mark_dirty)
                elif isinstance(w, (QTextEdit, QPlainTextEdit)):
                    w.textChanged.connect(self._mark_dirty)
                elif isinstance(w, (QDateEdit, QDateTimeEdit)):
                    try:
                        w.dateTimeChanged.connect(self._mark_dirty)
                    except Exception:
                        try:
                            w.dateChanged.connect(self._mark_dirty)
                        except Exception:
                            pass
            except Exception:
                pass

    def _wire_dirty_watchers(self):
        for w in [
            self.national_id ,self.archive,self.company, self.fiscal, self.entry, self.submit_date, self.due_date,
            self.upload_date, self.assess_date, self.assess_deadline, self.appeal_send,
            self.mad238_entry_date, self.mad238_agreement_deadline, self.penalty_amount
        ]:
            w.textChanged.connect(self._mark_dirty)
        self.deadline_days.valueChanged.connect(self._mark_dirty)
        for g in [ self.group_status, self.group_has_ass, self.group_report, self.group_objected]:
            for b in g.buttons():
                b.toggled.connect(self._mark_dirty)
        self._wire_panel_dirty_watchers(self.bodavi)
        self._wire_panel_dirty_watchers(self.tajdid)

        self._dirty_timer = QTimer(self)
        self._dirty_timer.timeout.connect(self._mark_dirty)
        self._dirty_timer.start(600)
        # اتصال برای QTextEdit/QPlainTextEdit و QDateEdit/QDateTimeEdit در سطح فرم
        for w in self.findChildren(QTextEdit) + self.findChildren(QPlainTextEdit):
            try:
                w.textChanged.connect(self._mark_dirty)
            except Exception:
                pass
        for w in self.findChildren(QDateEdit) + self.findChildren(QDateTimeEdit):
            try:
                w.dateTimeChanged.connect(self._mark_dirty)
            except Exception:
                try:
                    w.dateChanged.connect(self._mark_dirty)
                except Exception:
                    pass


    # ---------- Prefill ----------
    def _set_radio_by_text(self, group: QButtonGroup, target_text: str):
        for btn in group.buttons():
            if btn.text().strip() == (target_text or "").strip():
                btn.setChecked(True); return

    def _coerce_list(self, v):
        if v is None: return []
        if isinstance(v, list): return v
        return [v]

    def _coerce_uploaded(self, v):
        if not v: return []
        if isinstance(v, list):
            if all(isinstance(x, str) for x in v):
                return v[:]
            out = []
            for x in v:
                if isinstance(x, dict):
                    u = x.get("url") or x.get("path") or ""
                    if u: out.append(str(u))
            return out
        return [str(v)]

    def _load_record_into_form(self, idx: int):
        rec = fetch_record_from_sheet_by_id(self._record_id, self._spreadsheet_id, self._sa_json_path, self._sheet_name)
        if not rec:
            QMessageBox.critical(self, "خطا", "رکورد با این id در شیت پیدا نشد.")
            return
        self._original_record = rec
        r = self._original_record

        # پرکردن فرم به ماژول جدا منتقل شد
        prefill_editor_window(self, r)
        
        # Ensure 'نوع پرونده' multi-select is prefilled from record and disabled
        try:
            case_txt = (r.get('case_type') or '').strip()
            if case_txt and hasattr(self, 'case_checkboxes'):
                parts = [t.strip() for t in case_txt.replace('،', ',').split(',') if t.strip()]
                for cb in self.case_checkboxes:
                    cb.setChecked(cb.text() in parts)
            # If still nothing checked, default to the first option
            if getattr(self, 'case_checkboxes', []) and not any(cb.isChecked() for cb in self.case_checkboxes):
                self.case_checkboxes[0].setChecked(True)
            # Disable all case-type checkboxes (keep selected visually via theme)
            for cb in getattr(self, 'case_checkboxes', []):
                cb.setEnabled(False)
        except Exception:
            pass

        self._orig_snapshot = json.dumps(self._snapshot_current_form(), ensure_ascii=False, sort_keys=True)
        self._mark_dirty()

    def _save(self):
        
        nid = self.national_id.text().strip()
        if not (nid and nid.isdigit()):
            QMessageBox.warning(self, "اجباری", "شناسه ملی الزامی است")
            return
        archive = self.archive.text().strip()
        if not archive:
            QMessageBox.warning(self, "اجباری", "شماره بایگانی الزامی است")
            return
        company_name = self.company.text().strip()
        if not company_name:
            QMessageBox.warning(self, "اجباری", "نام شرکت الزامی است"); return

        fy = self.fiscal.text().strip()
        if not (fy.isdigit() and len(fy)==4):
            QMessageBox.warning(self, "اجباری", "سال مالی باید ۴ رقم باشد"); return

        ent_raw = self.entry.text()
        ent = ent_raw.strip()
        if ent.replace('_', '').replace('/', '').strip() == '':
            ent = ""

        # اگر کاربر وارد کرد، باید معتبر باشد
        if ent and not validate_jalali(ent):
            QMessageBox.warning(self, "نامعتبر", "تاریخ ورود به مؤسسه معتبر نیست .")
            return
        
        
        selected_cases = [cb.text() for cb in getattr(self, 'case_checkboxes', []) if cb.isChecked()]
        if not selected_cases:
            QMessageBox.warning(self, "اجباری", "حداقل یک نوع پرونده را انتخاب کنید"); return
        selected_cases_str = "، ".join(selected_cases)


        sub = self.submit_date.text().strip()
        if not validate_jalali(sub):
            QMessageBox.warning(self, "اجباری", "تاریخ ارائه اسناد و مدارک را وارد کنید"); return

        # محاسبه مهلت ارائه اسناد
        try:
            dd = jdatetime.datetime.strptime(sub, "%Y/%m/%d") + jdatetime.timedelta(days=self.deadline_days.value())
            due_str = dd.strftime("%Y/%m/%d")
            self.due_date.setText(due_str)
        except:
            QMessageBox.warning(self, "خطا", "محاسبه مهلت ارائه اسناد ممکن نشد")
            return

        due = self.due_date.text().strip()
        today_j = jdatetime.date.today()
        due_j = jdatetime.datetime.strptime(due, "%Y/%m/%d").date() if validate_jalali(due) else None

        # ساخت id یکتا برای رکورد


        # ✅ مسیر سریع اگر مهلت ارائه نگذشته
        if due_j and due_j > today_j:
            rec_quick = {
                'national_id': nid,
                'archive':archive,
                'company_name': self.company.text().strip(),
                'fiscal_year': fy,
                'entry_date': ent,
                'case_type': selected_cases_str,
                'submit_date': sub,
                'deadline_days': self.deadline_days.value() if self.deadline_days.value() != 0 else "",
                'due_date': due,
                'submit_status': (self.status_texts[self.group_status.checkedId()]
                                  if self.group_status.checkedId() >= 0 else ""),
                'upload_date': self.upload_date.text().strip() if (self.group_status.checkedId() == 0) else "",
                'uploaded_files': self.uploaded_files if (self.group_status.checkedId() == 0) else [],
                'has_assessment': "",
                'assessment_date': "",
                'assessment_deadline': "",
                'report_exists': "",
                'report_uploaded_files': [],
                'objected': "",
                'appeal_send_date': "",
                'petition_uploaded_files': [],
                'mad238_entry_date': "",
                'mad238_agreement_deadline': "",
                'jarime_amount': "",
                'notes': self.notes_w.get_notes(),
                'notify_days': self.global_settings.get('notify_days', ""),
                'notify_mode': self.global_settings.get('notify_mode', ""),
                'last_action_date': due,
                'reminder_notes': [],
                'status': "مهلت ارائه اسناد و مدارک"
            }
            return self._finalize(rec_quick)

        # از اینجا به بعد یعنی باید وضعیت مشخص شود
        status_id = self.group_status.checkedId()
        if status_id < 0:
            QMessageBox.warning(self, "اجباری", "وضعیت ارائه اسناد و مدارک را مشخص کنید")
            return
        status_txt = self.status_texts[status_id]  # 0: ارائه شد، 1: ارائه نشد

        # سه‌حالته برای بله/خیر/خالی
        id_ass = self.group_has_ass.checkedId()  # 1/0/-1
        id_rep = self.group_report.checkedId()   # 1/0/-1
        id_obj = self.group_objected.checkedId() # 1/0/-1
        has_ass = (id_ass == 1)

        has_assessment_val = "بله" if id_ass == 1 else ("خیر" if id_ass == 0 else "")
        report_exists_val = "بله" if id_rep == 1 else ("خیر" if id_rep == 0 else "")
        objected_val = "بله" if id_obj == 1 else ("خیر" if id_obj == 0 else "")

        assess_txt = self.assess_date.text().strip()
        if has_ass and not validate_jalali(assess_txt):
            QMessageBox.warning(self, "اجباری", "تاریخ صدور برگه تشخیص را وارد کنید")
            return
        amt_txt = self.penalty_amount.text().replace(",", "").strip()

        # اگر فقط «ارزش افزوده» تیک خورده باشد، مبلغ مالیات کلی اجباری نیست
        selected_cases_for_tax = [cb.text() for cb in getattr(self, 'case_checkboxes', []) if cb.isChecked()]
        only_vat = (len(selected_cases_for_tax) == 1 and "ارزش افزوده" in selected_cases_for_tax)


        amt_txt = self.penalty_amount.text().replace(",", "").strip()
        # در حالتی که فقط ارزش افزوده است، مبلغ مالیات کلی اجباری نیست
        if has_ass and (not only_vat) and not amt_txt:
            QMessageBox.warning(self, "اجباری", "مبلغ مالیات را وارد کنید")
            return


        # مقادیر تکمیلی جریمه و دوره‌های ارزش افزوده برای ذخیره
        perf_penalty_txt = ""
        if hasattr(self, "performance_penalty"):
            perf_penalty_txt = self.performance_penalty.text().replace(",", "").strip()

        vat_tax_vals = []
        vat_penalty_vals = []
        if hasattr(self, "vat_period_rows"):
            for _row_w, _tax_edit, _pen_edit in self.vat_period_rows:
                _t = _tax_edit.text().replace(",", "").strip()
                _p = _pen_edit.text().replace(",", "").strip()
                vat_tax_vals.append(_t)
                vat_penalty_vals.append(_p)
        # حداقل ۴ خانه برای دسترسی ایمن
        while len(vat_tax_vals) < 4:
            vat_tax_vals.append("")
        while len(vat_penalty_vals) < 4:
            vat_penalty_vals.append("")

        assess_deadline_str = ""
        if has_ass:
            ad = jdatetime.datetime.strptime(assess_txt, "%Y/%m/%d") + jdatetime.timedelta(days=30)
            assess_deadline_str = ad.strftime("%Y/%m/%d")
            self.assess_deadline.setText(assess_deadline_str)

        # --- اعتبارسنجی تاریخ اعتراض ---
        pet_raw = self.appeal_send.text()
        pet = pet_raw.strip()
        # اگر فقط ماسک خالی باشد (____/__/__)
        if pet.replace('_', '').replace('/', '').strip() == '':
            pet = ""

        # اگر «اعتراض شده؟» = بله باشد، تاریخ اعتراض اجباری و باید معتبر باشد
        if id_obj == 1:  # یعنی اعتراض شده = بله
            if not pet:
                QMessageBox.warning(self, "اجباری", "تاریخ اعتراض را وارد کنید")
                return
            if not validate_jalali(pet):
                QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ اعتراض معتبر نیست.")
                return
        else:
            # اگر اعتراض نشده، تاریخ اعتراض نباید ذخیره شود
            pet = ""

        rec_base = {
            'national_id': nid,
            'archive':archive,
            'company_name': self.company.text().strip(),
            'fiscal_year': fy,
            'entry_date': ent,
            'case_type': selected_cases_str,
            'submit_date': sub,
            'deadline_days': self.deadline_days.value() if self.deadline_days.value() != 0 else "",
            'due_date': due,
            'submit_status': status_txt,
            'upload_date': self.upload_date.text().strip() if status_id == 0 else "",
            'uploaded_files': self.uploaded_files if status_id == 0 else [],
            'has_assessment': has_assessment_val,
            'assessment_date': assess_txt if has_ass else "",
            'assessment_deadline': assess_deadline_str if has_ass else "",
            'report_exists': report_exists_val,
            'report_uploaded_files': self.report_uploaded_files if id_rep == 1 else [],
            'objected': objected_val,
            'appeal_send_date': pet if validate_jalali(pet) else "",
            'petition_uploaded_files': self.petition_uploaded_files,
            'mad238_entry_date': self.mad238_entry_date.text().strip(),
            'mad238_agreement_deadline': self.mad238_agreement_deadline.text().strip(),
            'jarime_amount': int(amt_txt) if (has_ass and amt_txt) else "",
            'performance_penalty': int(perf_penalty_txt) if (has_ass and perf_penalty_txt) else "",
            'vat_p1_tax': int(vat_tax_vals[0]) if vat_tax_vals[0] else "",
            'vat_p1_penalty': int(vat_penalty_vals[0]) if vat_penalty_vals[0] else "",
            'vat_p2_tax': int(vat_tax_vals[1]) if vat_tax_vals[1] else "",
            'vat_p2_penalty': int(vat_penalty_vals[1]) if vat_penalty_vals[1] else "",
            'vat_p3_tax': int(vat_tax_vals[2]) if vat_tax_vals[2] else "",
            'vat_p3_penalty': int(vat_penalty_vals[2]) if vat_penalty_vals[2] else "",
            'vat_p4_tax': int(vat_tax_vals[3]) if vat_tax_vals[3] else "",
            'vat_p4_penalty': int(vat_penalty_vals[3]) if vat_penalty_vals[3] else "",
            'notes': self.notes_w.get_notes(),
            'notify_days': self.global_settings.get('notify_days', ""),
            'notify_mode': self.global_settings.get('notify_mode', "")
        }

        # ===== ماده ۲۳۸ =====
        md_dead = rec_base['mad238_agreement_deadline']
        if validate_jalali(md_dead):
            md_j = jdatetime.datetime.strptime(md_dead, "%Y/%m/%d").date()
            has_result = self.rb_adjust.isChecked() or self.rb_refer.isChecked()

            # ۱) اگر مهلت در آینده است و هنوز نتیجه توافق انتخاب نشده:
            #    مثل قبل: فقط پرونده را با وضعیت «مهلت توافق ماده ۲۳۸» ثبت کن.
            if md_j > today_j and not has_result:
                rec_base['last_action_date'] = md_dead
                rec_base['reminder_notes'] = []
                rec_base['status'] = "مهلت توافق ماده ۲۳۸"
                return self._finalize(rec_base)

            # ۲) در بقیه حالت‌ها (مهلت گذشته، یا مهلت در آینده ولی نتیجه انتخاب شده)
            #    نتیجه باید حتماً مشخص باشد:
            if not has_result:
                QMessageBox.warning(self, "اجباری", "لطفاً نتیجه توافق ماده ۲۳۸ را مشخص کنید")
                return

            rec_base['mad238_result'] = "تعدیل مالیات" if self.rb_adjust.isChecked() else "ارجاع به هیأت بدوی"

            if self.rb_adjust.isChecked():
                dlg2 = AdjustConfirmDialog(self)
                if dlg2.exec() != QDialog.Accepted:
                    return
                if dlg2.get_decision():
                    rec_base['status'] = "مختومه"
                    dlg3 = FinalizeDialog(self)
                    if dlg3.exec() != QDialog.Accepted:
                        return
                    rec_base.update(dlg3.get_data())
                    rec_base['last_action_date'] = md_dead
                    rec_base['reminder_notes'] = []
                    return self._finalize(rec_base)
                else:
                    d = NextReminderDialog(self, status="تعدیل - پیگیری")
                    if d.exec() != QDialog.Accepted:
                        return
                    r = d.get_data()
                    if not validate_jalali(r['next_date']) or jdatetime.datetime.strptime(r['next_date'], "%Y/%m/%d").date() < today_j:
                        QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ یادآوری بعدی نباید گذشته باشد")
                        return
                    rec_base['last_action_date'] = r['next_date']
                    rec_base['reminder_notes'] = r['reminder_notes']
                    rec_base['status'] = r.get('status') or "پیگیری تعدیل"
                    return self._finalize(rec_base)

            if self.rb_refer.isChecked():
                if not hasattr(self, 'bodavi') or not hasattr(self.bodavi, 'validate_and_collect'):
                    QMessageBox.warning(self, "خطا", "پنل هیأت بدوی در دسترس/به‌روز نیست")
                    return

                b_data, b_finalize, b_reminder, b_status, b_err = self.bodavi.validate_and_collect(today_j)

                if b_err == "empty":
                    d = NextReminderDialog(self, status="جلسه اول هیأت بدوی")
                    if d.exec() != QDialog.Accepted:
                        return
                    r = d.get_data()
                    if (not validate_jalali(r['next_date']) or
                        jdatetime.datetime.strptime(r['next_date'], "%Y/%m/%d").date() < today_j):
                        QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ یادآوری بعدی نباید گذشته باشد")
                        return
                    rec_base.update({
                        'last_action_date': r['next_date'],
                        'reminder_notes': r['reminder_notes'],
                        'status': r.get('status') or "جلسه اول هیأت بدوی",
                        'bodavi_session_date': ""
                    })
                    return self._finalize(rec_base)

                if b_err == "invest-missing":
                    QMessageBox.warning(self, "اجباری", "نیاز به تحقیق و کارشناسی را مشخص کن")
                    return

                if b_err == "verdict-missing":
                    d = NextReminderDialog(self, status="پیگیری پرونده بدوی")
                    if d.exec() != QDialog.Accepted:
                        return
                    r = d.get_data()
                    if (not validate_jalali(r['next_date']) or
                        jdatetime.datetime.strptime(r['next_date'], "%Y/%m/%d").date() < today_j):
                        QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ یادآوری بعدی نباید گذشته باشد")
                        return
                    self._merge_bodavi_into_rec(rec_base, b_data or {})
                    rec_base['last_action_date'] = r['next_date']
                    rec_base['reminder_notes'] = r['reminder_notes']
                    rec_base['status'] = r.get('status') or "پیگیری پرونده بدوی"
                    return self._finalize(rec_base)

                if b_err == "obj-missing":
                    QMessageBox.warning(self, "اجباری", "اعتراض به رأی بدوی انجام شده یا نه را انتخاب کنید")
                    return
                if b_err == "verdict-result-missing":
                    QMessageBox.warning(self, "اجباری", "رأی هیأت بدوی را انتخاب کنید")
                    return
                if b_err == "obj-date-missing":
                    QMessageBox.warning(self, "اجباری", "تاریخ اعتراض به رأی بدوی را وارد کنید")
                    return

                self._merge_bodavi_into_rec(rec_base, b_data)

                if b_data and b_data.get('objection_done') == 'بله':
                    if not hasattr(self, 'tajdid') or not hasattr(self.tajdid, 'validate_and_collect'):
                        QMessageBox.warning(self, "خطا", "پنل هیأت تجدیدنظر در دسترس/به‌روز نیست")
                        return

                    t_data, t_finalize, t_reminder, t_status, t_err = self.tajdid.validate_and_collect(today_j)

                    if t_err == "empty":
                        d = NextReminderDialog(self, status="جلسه اول هیأت تجدید نظر")
                        if d.exec() != QDialog.Accepted:
                            return
                        r = d.get_data()
                        if (not validate_jalali(r['next_date']) or
                            jdatetime.datetime.strptime(r['next_date'], "%Y/%m/%d").date() < today_j):
                            QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ یادآوری بعدی نباید گذشته باشد")
                            return
                        rec_base.update({
                            'last_action_date': r['next_date'],
                            'reminder_notes': r['reminder_notes'],
                            'status': r.get('status') or "جلسه اول هیأت تجدید نظر",
                            'tajdid_refer_date': ""
                        })
                        return self._finalize(rec_base)

                    if t_err == "invest-missing":
                        QMessageBox.warning(self, "اجباری", "نیاز به تحقیق و کارشناسی را مشخص کن")
                        return
                    if t_err == "verdict-missing":
                        d = NextReminderDialog(self, status="پیگیری پرونده تجدیدنظر")
                        if d.exec() != QDialog.Accepted:
                            return
                        r = d.get_data()
                        if (not validate_jalali(r['next_date']) or
                            jdatetime.datetime.strptime(r['next_date'], "%Y/%m/%d").date() < today_j):
                            QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ یادآوری بعدی نباید گذشته باشد")
                            return
                        self._merge_tajdid_into_rec(rec_base, t_data or {})
                        rec_base['last_action_date'] = r['next_date']
                        rec_base['reminder_notes'] = r['reminder_notes']
                        rec_base['status'] = r.get('status') or "پیگیری پرونده تجدیدنظر"
                        return self._finalize(rec_base)
                    if t_err == "obj-missing":
                        QMessageBox.warning(self, "اجباری", "درخواست ۲۵۱ را مشخص کنید")
                        return
                    if t_err == "verdict-result-missing":
                        QMessageBox.warning(self, "اجباری", "نتیجه رأی تجدیدنظر را انتخاب کنید")
                        return
                    if t_err == "obj-date-missing":
                        QMessageBox.warning(self, "اجباری", "تاریخ ثبت درخواست ۲۵۱ را وارد کنید")
                        return
                    self._merge_tajdid_into_rec(rec_base, t_data)


                    # --- New tajdid flow overrides (v2) ---
                    # 1) اگر تاریخ جلسه شورا آینده/امروز باشد، به عنوان آخرین اقدام ثبت شود
                    _cdate = rec_base.get('council_date') or (t_data or {}).get('council_date')
                    try:
                        if _cdate and validate_jalali(_cdate):
                            _cdate_j = jdatetime.datetime.strptime(_cdate, "%Y/%m/%d").date()
                            if _cdate_j >= today_j:
                                rec_base['last_action_date'] = _cdate
                    except Exception:
                        pass

                    _verify = (t_data or {}).get('verification_status') or rec_base.get('verification_status')
                    # درخواست تجدید رسیدگی ماده ۲۵۱ انجام شده = بله
                    _m251 = (t_data or {}).get('objection_done_tajdid') or (t_data or {}).get('request_251_done') or (t_data or {}).get('m251_done') or (t_data or {}).get('done_251') or (t_data or {}).get('درخواست_۲۵۱_انجام_شده')

                    def _is_yes(v):
                        return str(v).strip() in ('بله','Yes','yes','TRUE','True','1')

                    # 3) اگر احراز دبیرخانه شورا = خیر (اختیاری) → فرم تعیین مبلغ نهایی و مختومه (بر هرچیز مقدم)
                    if _verify == 'خیر':
                        dlg = FinalizeDialog(self)
                        if dlg.exec() != QDialog.Accepted:
                            return
                        rec_base.update(dlg.get_data())
                        rec_base['status'] = 'مختومه'
                        return self._finalize(rec_base)

                    # 4) اگر احراز دبیرخانه شورا = بله → اگر تاریخ شورا خالی/گذشته بود، فرم یادآوری؛ اگر امروز/آینده بود، همان تاریخ ثبت شود (این هم مقدم بر ۲۵۱)
                    if _verify == 'بله':
                        _cdate2 = rec_base.get('council_date') or (t_data or {}).get('council_date')
                        try:
                            if _cdate2 and validate_jalali(_cdate2):
                                _cdate2_j = jdatetime.datetime.strptime(_cdate2, "%Y/%m/%d").date()
                                if _cdate2_j >= today_j:
                                    rec_base['last_action_date'] = _cdate2
                                    rec_base['status'] = 'جلسه شورا'
                                    return self._finalize(rec_base)
                        except Exception:
                            pass
                        d = NextReminderDialog(self, status="پیگیری پرونده تجدیدنظر")
                        if d.exec() != QDialog.Accepted:
                            return
                        r = d.get_data()
                        if (not validate_jalali(r['next_date']) or
                            jdatetime.datetime.strptime(r['next_date'], "%Y/%m/%d").date() < today_j):
                            QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ یادآوری بعدی نباید گذشته باشد")
                            return
                        rec_base['last_action_date'] = r['next_date']
                        rec_base['reminder_notes'] = r['reminder_notes']
                        rec_base['status'] = r.get('status') or "پیگیری پرونده تجدیدنظر"
                        return self._finalize(rec_base)

                    # 2) اگر م۲۵۱ انجام شده = بله → فرم تاریخ یادآوری بعدی (بعد از احراز)
                    if _is_yes(_m251):
                        d = NextReminderDialog(self, status="پیگیری پرونده تجدیدنظر")
                        if d.exec() != QDialog.Accepted:
                            return
                        r = d.get_data()
                        if (not validate_jalali(r['next_date']) or
                            jdatetime.datetime.strptime(r['next_date'], "%Y/%m/%d").date() < today_j):
                            QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ یادآوری بعدی نباید گذشته باشد")
                            return
                        rec_base['last_action_date'] = r['next_date']
                        rec_base['reminder_notes'] = r['reminder_notes']
                        rec_base['status'] = r.get('status') or "پیگیری پرونده تجدیدنظر"
                        return self._finalize(rec_base)


                    # 3) اگر احراز دبیرخانه شورا = خیر (اختیاری) → فرم تعیین مبلغ نهایی و مختومه
                    if _verify == 'خیر':
                        dlg = FinalizeDialog(self)
                        if dlg.exec() != QDialog.Accepted:
                            return
                        rec_base.update(dlg.get_data())
                        rec_base['status'] = 'مختومه'
                        return self._finalize(rec_base)

                    if _verify == 'بله':
                        _cdate2 = rec_base.get('council_date') or (t_data or {}).get('council_date')
                        try:
                            if _cdate2 and validate_jalali(_cdate2):
                                _cdate2_j = jdatetime.datetime.strptime(_cdate2, "%Y/%m/%d").date()
                                if _cdate2_j >= today_j:
                                    rec_base['last_action_date'] = _cdate2
                                    rec_base['status'] = 'جلسه شورا'
                                    return self._finalize(rec_base)
                        except Exception:
                            pass
                        d = NextReminderDialog(self, status="پیگیری پرونده تجدیدنظر")
                        if d.exec() != QDialog.Accepted:
                            return
                        r = d.get_data()
                        if (not validate_jalali(r['next_date']) or
                            jdatetime.datetime.strptime(r['next_date'], "%Y/%m/%d").date() < today_j):
                            QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ یادآوری بعدی نباید گذشته باشد")
                            return
                        rec_base['last_action_date'] = r['next_date']
                        rec_base['reminder_notes'] = r['reminder_notes']
                        rec_base['status'] = r.get('status') or "پیگیری پرونده تجدیدنظر"
                        return self._finalize(rec_base)
                    if t_reminder:
                        d = NextReminderDialog(self, status=(t_status or "پیگیری پرونده تجدیدنظر"))
                        if d.exec() != QDialog.Accepted:
                            return
                        r = d.get_data()
                        if (not validate_jalali(r['next_date']) or
                            jdatetime.datetime.strptime(r['next_date'], "%Y/%m/%d").date() < today_j):
                            QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ یادآوری بعدی نباید گذشته باشد")
                            return
                        rec_base['last_action_date'] = r['next_date']
                        rec_base['reminder_notes'] = r['reminder_notes']
                        rec_base['status'] = r.get('status') or (t_status or "پیگیری پرونده تجدیدنظر")
                        return self._finalize(rec_base)

                    if t_finalize:
                        dlg = FinalizeDialog(self)
                        if dlg.exec() != QDialog.Accepted:
                            return
                        rec_base.update(dlg.get_data())
                        if 'last_action_date' not in rec_base or not rec_base['last_action_date']:
                            rec_base['last_action_date'] = (
                                rec_base.get('council_date') or
                                rec_base.get('verdict_date_tajdid') or
                                rec_base.get('objection_deadline_tajdid') or
                                rec_base.get('due_date', '')
                            )
                        rec_base.setdefault('reminder_notes', [])
                        return self._finalize(rec_base)
                    return self._finalize(rec_base)

                if b_reminder:
                    d = NextReminderDialog(self, status=(b_status or "پیگیری پرونده بدوی"))
                    if d.exec() != QDialog.Accepted:
                        return
                    r = d.get_data()
                    if (not validate_jalali(r['next_date']) or
                        jdatetime.datetime.strptime(r['next_date'], "%Y/%m/%d").date() < today_j):
                        QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ یادآوری بعدی نباید گذشته باشد")
                        return
                    rec_base['last_action_date'] = r['next_date']
                    rec_base['reminder_notes'] = r['reminder_notes']
                    rec_base['status'] = r.get('status') or (b_status or "پیگیری پرونده بدوی")
                    return self._finalize(rec_base)

                if b_finalize:
                    dlg = FinalizeDialog(self)
                    if dlg.exec() != QDialog.Accepted:
                        return
                    rec_base.update(dlg.get_data())
                    if 'last_action_date' not in rec_base or not rec_base['last_action_date']:
                        rec_base['last_action_date'] = rec_base.get('bodavi_verdict_date', rec_base.get('due_date', ''))
                    rec_base.setdefault('reminder_notes', [])
                    return self._finalize(rec_base)

                return self._finalize(rec_base)

        if rec_base['has_assessment'] == "بله" and validate_jalali(rec_base['assessment_deadline']):
            ad_j = jdatetime.datetime.strptime(rec_base['assessment_deadline'], "%Y/%m/%d").date()
            if ad_j > today_j:
                rec_base['last_action_date'] = rec_base['assessment_deadline']
                rec_base['reminder_notes'] = []
                rec_base['status'] = "مهلت اعتراض برگه تشخیص"
                return self._finalize(rec_base)
            if self.group_report.checkedId() < 0:
                QMessageBox.warning(self, "اجباری", "گزارش رسیدگی را انتخاب کنید")
                return
            if self.group_report.checkedId() == 1 and self.group_objected.checkedId() < 0:
                QMessageBox.warning(self, "اجباری", "اعتراض شده را انتخاب کنید")
                return

        if status_id == 0:
            d = NextReminderDialog(self, status="پیگیری مدارک")
            if d.exec() != QDialog.Accepted:
                return
            r = d.get_data()
            if not validate_jalali(r['next_date']) or jdatetime.datetime.strptime(r['next_date'], "%Y/%m/%d").date() < today_j:
                QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ یادآوری بعدی نباید گذشته باشد")
                return
            rec_base['last_action_date'] = r['next_date']
            rec_base['reminder_notes'] = r['reminder_notes']
            rec_base['status'] = r.get('status') or "پیگیری مدارک"
            return self._finalize(rec_base)

        # سایر مسیرها (لایحه/...)
        pet = rec_base.get('appeal_send_date', '')
        if validate_jalali(pet):
            pet_j = jdatetime.datetime.strptime(pet, "%Y/%m/%d").date()
            if pet_j > today_j:
                last, rem = pet, []
            else:
                d = NextReminderDialog(self, status="پیگیری لایحه")
                if d.exec() != QDialog.Accepted:
                    return
                r = d.get_data()
                if not validate_jalali(r['next_date']) or jdatetime.datetime.strptime(r['next_date'], "%Y/%m/%d").date() < today_j:
                    QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ یادآوری بعدی نباید گذشته باشد")
                    return
                last, rem = r['next_date'], r['reminder_notes']
            rec_base['last_action_date'] = last
            rec_base['reminder_notes'] = rem
            rec_base['status'] = "پیگیری لایحه" if last != pet else "ارسال لایحه"
            return self._finalize(rec_base)

        d = NextReminderDialog(self, status="پیگیری")
        if d.exec() != QDialog.Accepted:
            return
        r = d.get_data()
        if not validate_jalali(r['next_date']) or jdatetime.datetime.strptime(r['next_date'], "%Y/%m/%d").date() < today_j:
            QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ یادآوری بعدی نباید گذشته باشد")
            return
        rec_base['last_action_date'] = r['next_date']
        rec_base['reminder_notes'] = r['reminder_notes']
        rec_base['status'] = r.get('status') or "پیگیری"
        return self._finalize(rec_base)

    def _merge_bodavi_into_rec(self, rec_base: dict, data: dict):
        if not data:
            return
        rec_base.update({
            'bodavi_session_date':    data.get('refer_date', ''),
            'bodavi_verdict_date':    data.get('verdict_date', ''),
            'bodavi_appeal_deadline': data.get('objection_deadline', ''),
            'bodavi_appeal_done':     data.get('objection_done', ''),
            'bodavi_appeal_date':     data.get('objection_date', ''),
            'bodavi_verdict':         data.get('verdict_result', ''),
            'needs_investigation':    data.get('needs_investigation', ''),
            'expert_order_date':      data.get('expert_order_date', ''),
        })
        if data.get('status'):
            rec_base['status'] = data['status']
        if data.get('last_action_date'):
            rec_base['last_action_date'] = data['last_action_date']
        if 'reminder_notes' in data:
            rec_base['reminder_notes'] = data.get('reminder_notes', [])

    def _merge_tajdid_into_rec(self, rec_base: dict, d: dict):
        if not d:
            return
        rec_base.update({
            'tajdid_refer_date':        d.get('tajdid_refer_date', ''),
            'verdict_date_tajdid':      d.get('verdict_date_tajdid', ''),
            'objection_deadline_tajdid':d.get('objection_deadline_tajdid', ''),
            'objection_done_tajdid':    d.get('objection_done_tajdid', ''),
            'objection_date_tajdid':    d.get('objection_date_tajdid', ''),
            'verdict_result_tajdid':    d.get('verdict_result_tajdid', ''),
            'verification_status':      d.get('verification_status', ''),
            'council_date':             d.get('council_date', ''),
            'needs_investigation_tajdid': d.get('needs_investigation_tajdid', ''),
            'tajdid_expert_date':        d.get('tajdid_expert_date', ''),
        })
        if d.get('status'):
            rec_base['status'] = d['status']
        if d.get('last_action_date'):
            rec_base['last_action_date'] = d['last_action_date']
        if 'reminder_notes' in d:
            rec_base['reminder_notes'] = d.get('reminder_notes', [])
    # ---------- نهایی‌سازی ----------
    def _finalize(self, full_record: dict):
        """کل سطر را بازنویسی می‌کند؛ ادغام با رکورد قدیمی انجام نمی‌دهیم."""
        try:
            rec_id = self._record_id
            if not rec_id:
                QMessageBox.critical(self, "خطا", "id رکورد نامشخص است."); return

            # اطمینان از کامل بودن کلیدها
            row_to_send = {h: "" for h in DEFAULT_HEADER}
            row_to_send.update(full_record)
            row_to_send["id"] = rec_id

            try:
                QApplication.setOverrideCursor(Qt.WaitCursor)
            except Exception:
                pass
            try:
                if hasattr(self, "status_lbl"):
                    self.status_lbl.setText("در حال ذخیره در شیت…")
                result = upsert_record_to_sheet(
                    rec=row_to_send,
                    spreadsheet_id=self._spreadsheet_id,
                    sa_json_path=self._sa_json_path,
                    sheet_name=self._sheet_name,
                    status_label=getattr(self, "status_lbl", None)
                )
            finally:
                try:
                    QApplication.restoreOverrideCursor()
                except Exception:
                    pass

            QMessageBox.information(self, "انجام شد", f"در شیت {('به‌روزرسانی' if result=='updated' else 'درج')} شد.")
            if hasattr(self, "accept"):
                try: self.accept()
                except Exception: pass

        except Exception as e:
            try:
                QApplication.restoreOverrideCursor()
            except Exception:
                pass
            QMessageBox.critical(self, "خطا", f"ذخیره در شیت ناموفق بود:\n{e}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record-id", type=str, required=True, help="شناسهٔ رکورد برای ویرایش")
    ap.add_argument("--sheet-id", "--spreadsheet-id", dest="sheet_id", type=str, default=os.environ.get("GOOGLE_SHEETS_KEY"))
    ap.add_argument("--sheet-name", "--sheet", dest="sheet_name", type=str, default=os.environ.get("GOOGLE_SHEET_NAME", "Sheet1"))
    ap.add_argument("--sa-json", type=str, default=os.environ.get("GOOGLE_SA_JSON"))
    args = ap.parse_args()

    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    _load_qss(app)
    w = EditorWindow(record_id=args.record_id,
                     spreadsheet_id=args.sheet_id,
                     sa_json_path=args.sa_json,
                     sheet_name=args.sheet_name)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()


# ---- Explicit EditWindow class (no fallback to using the name EditorWindow directly) ----
try:
    class EditWindow(EditorWindow):  # identical behavior, just different public name
        pass
except NameError:
    # If the source already defines EditWindow natively, leave as is.
    pass
