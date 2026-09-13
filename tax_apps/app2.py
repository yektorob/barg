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

# tax_apps/app2.py
# -*- coding: utf-8 -*-

import os
import sys
import json
import re
import datetime
import jdatetime
import subprocess
from functools import partial

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, Signal

from tax_logic import load_activities, save_activity, delete_activity

# ---------- اندازهٔ پنجرهٔ ویرایش (هماهنگ با Editor اپ۳) ----------
EDITOR_MIN_W, EDITOR_MIN_H = 860, 560
EDITOR_MAX_W, EDITOR_MAX_H = 1100, 820




# ---------------- Utils ----------------
_P2E = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
_ZW = ''.join(['\u200c', '\u200f', '\u200e', '\u202a', '\u202b', '\u202c', '\u202d', '\u202e', '\u00a0'])

DAY_NAMES = ['شنبه','یکشنبه','دوشنبه','سه\u200cشنبه','چهارشنبه','پنجشنبه','جمعه']
JALALI_MONTHS = ['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور','مهر','آبان','آذر','دی','بهمن','اسفند']

def normalize_digits_and_seps(s: str) -> str:
    if not isinstance(s, str): return ''
    s = s.translate(_P2E)
    for ch in _ZW:
        s = s.replace(ch, '')
    s = s.strip().replace('-', '/')
    s = re.sub(r'\s+', '', s)
    return s

def parse_jalali_date_str(s):
    if not s: return None
    s = normalize_digits_and_seps(s)
    if s in ('', '//'): return None
    m = re.match(r'^(\d{3,4})/(\d{1,2})/(\d{1,2})$', s)
    if not m: return None
    y, mo, d = map(int, m.groups())
    if not (1200 <= y <= 1700 and 1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}/{mo:02d}/{d:02d}"

def to_persian_digits(s):
    return str(s).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))

def _div(a, b): return a // b

def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0,31,59,90,120,151,181,212,243,273,304,334]
    if gy > 1600:
        jy = 979; gy -= 1600
    else:
        jy = 0; gy -= 621
    gy2 = (gy + 1) if gm > 2 else gy
    days = 365*gy + _div(gy2+3,4) - _div(gy2+99,100) + _div(gy2+399,400) - 80 + gd + g_d_m[gm-1]
    jy += 33*(days//12053); days %= 12053
    jy += 4*(days//1461);   days %= 1461
    if days > 365:
        jy += (days-1)//365; days = (days-1)%365
    if days < 186:
        jm = 1 + days//31; jd = 1 + (days%31)
    else:
        days -= 186; jm = 7 + days//30; jd = 1 + (days%30)
    return jy, jm, jd

def start_of_week_saturday(date: datetime.date) -> datetime.date:
    days_since_sat = (date.weekday() - 5) % 7
    return date - datetime.timedelta(days=days_since_sat)


# ================ دیالوگ تعیین تاریخ یادآوری بعدی ================
class SimpleNotesWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ReminderNotesWidget")
        self.v = QtWidgets.QVBoxLayout(self)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(6)

        self.btn_add = QtWidgets.QPushButton("➕ افزودن یادداشت")
        self.btn_add.setEnabled(False)
        self.btn_add.clicked.connect(self._add_note)
        self.v.addWidget(self.btn_add, 0, Qt.AlignRight)

        self.items_wrap = QtWidgets.QVBoxLayout()
        self.items_wrap.setContentsMargins(0, 0, 0, 0)
        self.items_wrap.setSpacing(6)
        self.v.addLayout(self.items_wrap)

        self._entries = []

    def set_add_enabled(self, enabled: bool):
        try:
            self.btn_add.setEnabled(bool(enabled))
        except Exception:
            pass

    def _add_note(self, default_text=""):
        row = QtWidgets.QFrame(self)
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)

        te = QtWidgets.QTextEdit(row)
        te.setObjectName("ReminderNoteText")
        te.setFixedHeight(64)
        te.setPlainText(default_text or "")

        btn_del = QtWidgets.QPushButton("🗑️")
        btn_del.setFixedHeight(32)

        def _remove():
            try:
                self._entries = [(f,t) for (f,t) in self._entries if f is not row]
                row.setParent(None)
            except Exception:
                pass
        btn_del.clicked.connect(_remove)

        h.addWidget(te, 1)
        h.addWidget(btn_del, 0, Qt.AlignTop)
        self.items_wrap.addWidget(row)
        self._entries.append((row, te))

    def get_notes(self):
        out = []
        for _, te in self._entries:
            try:
                s = te.toPlainText().strip()
                if s:
                    out.append(s)
            except Exception:
                continue
        return out

    def clear(self):
        for f, _ in list(self._entries):
            try:
                f.setParent(None)
            except Exception:
                pass
        self._entries.clear()


class NextReminderDialog(QtWidgets.QDialog):
    def __init__(self, initial_value: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("NextReminderDialogRoot")
        self.setWindowTitle("تاریخ یادآوری بعدی")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(420)

        lay = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()

        self.input = QtWidgets.QLineEdit()
        # ماسک همیشه فعال، مثل اپ۳
        self.input.setInputMask("0000/00/00;_")
        self.input.setPlaceholderText("۱۴۰۳/۰۷/۰۱")  # نمونهٔ شمسی برای هدایت کاربر
        if initial_value:
            self.input.setText(str(initial_value).replace("-", "/"))

        form.addRow("تاریخ:", self.input)
        lay.addLayout(form)

        # یادداشت‌های یادآوری
        self.lbl_notes = QtWidgets.QLabel("یادداشت‌های یادآوری:")
        self.lbl_notes.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(self.lbl_notes)

        self.notes = SimpleNotesWidget(self)
        lay.addWidget(self.notes)

        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        self.btn_ok = QtWidgets.QPushButton("ذخیره")
        self.btn_ok.setEnabled(False)
        btn_cancel = QtWidgets.QPushButton("انصراف")
        row.addWidget(self.btn_ok)
        row.addWidget(btn_cancel)
        lay.addLayout(row)

        self._initial_norm = self._normalize(initial_value)
        self.input.textChanged.connect(self._on_text_changed)
        self.btn_ok.clicked.connect(self._on_ok)
        btn_cancel.clicked.connect(self.reject)

        # استایل هماهنگ
        self.setStyleSheet("""
#NextReminderDialogRoot { background:#1E1E1E; }
QLabel { color:#F5F5F5; }
QLineEdit {
    border:1px solid #383838; border-radius:10px; padding:8px 12px;
    background:#0E0E0E; color:#F5F5F5; selection-background-color:#3A86FF;
}
QPushButton {
    border:none; border-radius:17px; min-height:34px; padding:0 14px;
    background:#3A86FF; color:#FFFFFF;
}
QPushButton:hover { background:#3479E6; }
QPushButton:disabled { background:#2C2E33; color:#9AA0A6; }
""")

    def _normalize(self, s: str) -> str:
        s = normalize_digits_and_seps(s or "")
        m = re.match(r'^(\d{3,4})/(\d{1,2})/(\d{1,2})$', s)
        if not m:
            return ""
        y, mo, d = m.groups()
        if len(y) == 3:
            y = "1" + y
        return f"{int(y):04d}/{int(mo):02d}/{int(d):02d}"

    def _on_text_changed(self, _):
        cur = self._normalize(self.input.text())
        enabled = bool(cur) and cur != self._initial_norm
        self.btn_ok.setEnabled(enabled)
        try:
            self.notes.set_add_enabled(enabled)
        except Exception:
            pass

    def _on_ok(self):
        cur = self._normalize(self.input.text())
        if not cur:
            QtWidgets.QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ شمسی معتبر وارد کنید (YYYY/MM/DD)")
            self.input.setFocus()
            self.input.selectAll()
            return
        # مقایسه با امروز جلالی
        today = jdatetime.date.today()
        try:
            jdate = jdatetime.datetime.strptime(cur, "%Y/%m/%d").date()
        except Exception:
            QtWidgets.QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ شمسی معتبر وارد کنید (YYYY/MM/DD)")
            self.input.setFocus()
            self.input.selectAll()
            return
        if jdate < today:
            QtWidgets.QMessageBox.warning(self, "تاریخ گذشته", "تاریخ یادآوری نباید قبل از امروز باشد.")
            self.input.setFocus()
            self.input.selectAll()
            return
        self.btn_ok.setEnabled(True)
        self.accept()

    def get_value(self) -> str:
        return self._normalize(self.input.text())

    def get_notes(self) -> list:
        try:
            return list(self.notes.get_notes())
        except Exception:
            return []


class DayCardWidget(QtWidgets.QFrame):
    clicked = Signal()

    def __init__(self, day_name: str, parent=None):
        super().__init__(parent)
        self.setObjectName("DayCard")
        self.setProperty("selected", False)

        self.setFixedSize(168, 110)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        self.lblDay = QtWidgets.QLabel(day_name, self)
        self.lblDay.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        f1 = self.lblDay.font(); f1.setPointSize(12); f1.setBold(True)
        self.lblDay.setFont(f1)

        self.lblDate = QtWidgets.QLabel("—", self)
        self.lblDate.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        f2 = self.lblDate.font(); f2.setPointSize(22); f2.setBold(True)
        self.lblDate.setFont(f2)

        lay.addWidget(self.lblDay)
        lay.addWidget(self.lblDate)

        # badge قرمز بالا-چپ
        self.badge = QtWidgets.QLabel("", self)
        self.badge.setObjectName("Badge")
        self.badge.setFixedSize(22, 22)
        self.badge.move(8, 8)
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.hide()

        self.setCursor(Qt.PointingHandCursor)

    def set_date_number(self, jd: int):
        self.lblDate.setText(to_persian_digits(jd))

    def set_count(self, n: int):
        if n and n > 0:
            self.badge.setText(to_persian_digits(n))
            self.badge.show()
        else:
            self.badge.hide()

    def set_selected(self, sel: bool):
        self.setProperty("selected", sel)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


# --------------- Action Card ---------------
class ActionCardWidget(QtWidgets.QFrame):
    def __init__(self, title_company: str, status_text: str, date_text: str,
                 with_edit=False, on_edit=None, on_next_reminder=None, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoCard")
        self.setMinimumHeight(86)
        self.setLayoutDirection(Qt.RightToLeft)

        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        info_box = QtWidgets.QVBoxLayout()
        info_box.setContentsMargins(0, 0, 0, 0)
        info_box.setSpacing(6)
        info_box.setAlignment(Qt.AlignRight)

        lbl_title = QtWidgets.QLabel(f"نام شرکت: {title_company}")
        f1 = lbl_title.font(); f1.setPointSize(12); f1.setBold(True)
        lbl_title.setFont(f1)
        lbl_title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_title.setLayoutDirection(Qt.RightToLeft)

        lbl_details = QtWidgets.QLabel(f"وضعیت: {status_text}    |    آخرین اقدام: {to_persian_digits(date_text)}")
        f2 = lbl_details.font(); f2.setPointSize(11)
        lbl_details.setFont(f2)
        lbl_details.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_details.setLayoutDirection(Qt.RightToLeft)

        info_box.addWidget(lbl_title)
        info_box.addWidget(lbl_details)

        lay.addLayout(info_box, 1)

        if with_edit:
            # دکمه یادآوری کنار ویرایش
            btn_next = QtWidgets.QPushButton("تاریخ یادآوری بعدی…")
            btn_next.setObjectName("EditBtn")
            btn_next.setCursor(Qt.PointingHandCursor)
            btn_next.setFixedHeight(34)
            btn_next.clicked.connect(lambda: on_next_reminder() if callable(on_next_reminder) else None)
            lay.addWidget(btn_next, 0, Qt.AlignVCenter)

            btn = QtWidgets.QPushButton("ویرایش")
            btn.setObjectName("EditBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(34)
            btn.clicked.connect(lambda: on_edit() if callable(on_edit) else None)
            lay.addWidget(btn, 0, Qt.AlignVCenter)


# --------------- Custom List Widget ---------------
class RTLListWidget(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFlow(QtWidgets.QListView.TopToBottom)
        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setSpacing(8)
        self.setUniformItemSizes(False)


# ---------------- Main App2Widget ----------------
class App2Widget(QtWidgets.QWidget):
    """
    تقویم هفتگی + کارت‌های اقدامات
    companies.json از ریشهٔ پروژه خوانده می‌شود.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TaxApp2Root")
        self.setLayoutDirection(Qt.RightToLeft)

        self.today = datetime.date.today()
        self.week_anchor = start_of_week_saturday(self.today)
        self.selected_date = self.today

        self.data = []
        self.actions_by_date = {}
        self.overdue_actions = []

        self._build_ui()
        self._load_data()
        self._rebuild_ui_state()

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._maybe_reload_sheet)
        self._timer.start(15000)

    # ---------- UI ----------
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)
        root.setAlignment(Qt.AlignRight)

        # برچسب ماه - راست‌چین
        self.lbl_month = QtWidgets.QLabel("")
        self.lbl_month.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_month.setLayoutDirection(Qt.RightToLeft)
        f = self.lbl_month.font(); f.setPointSize(16); f.setBold(True)
        self.lbl_month.setFont(f)
        root.addWidget(self.lbl_month)

        # تقویم هفتگی: داخل کانتینر RTL
        week_container = QtWidgets.QWidget()
        week_container.setLayoutDirection(Qt.RightToLeft)
        week_row = QtWidgets.QHBoxLayout(week_container)
        week_row.setContentsMargins(0, 0, 0, 0)
        week_row.setSpacing(8)
        root.addWidget(week_container)

        week_row.addStretch(1)

        self.btn_prev = QtWidgets.QPushButton(">")
        self.btn_prev.setObjectName("NavTinyBtn")
        self.btn_prev.setFixedSize(38, 34)
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        week_row.addWidget(self.btn_prev, 0, Qt.AlignVCenter)

        cards_wrap = QtWidgets.QWidget()
        cards_wrap.setLayoutDirection(Qt.RightToLeft)
        self.cards_layout = QtWidgets.QHBoxLayout(cards_wrap)
        self.cards_layout.setContentsMargins(8, 0, 8, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setAlignment(Qt.AlignRight)

        self.cards = []
        for i, name in enumerate(DAY_NAMES):
            card = DayCardWidget(name)
            card.clicked.connect(partial(self._on_day_clicked, i))
            self.cards.append(card)
            self.cards_layout.addWidget(card, 0, Qt.AlignVCenter)

        week_row.addWidget(cards_wrap, 0, Qt.AlignVCenter)

        self.btn_next = QtWidgets.QPushButton("<")
        self.btn_next.setObjectName("NavTinyBtn")
        self.btn_next.setFixedSize(38, 34)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        week_row.addWidget(self.btn_next, 0, Qt.AlignVCenter)

        week_row.addStretch(1)

        # عنوان و لیست «اقدامات»
        title1 = QtWidgets.QLabel("اقدامات")
        f1 = title1.font(); f1.setPointSize(13); f1.setBold(True)
        title1.setFont(f1)
        title1.setAlignment(Qt.AlignRight)
        title1.setLayoutDirection(Qt.RightToLeft)
        root.addWidget(title1)

        self.list_actions = RTLListWidget()
        self.list_actions.setObjectName("ListCard")
        root.addWidget(self.list_actions, 1)

        # عنوان و لیست «اقدامات با وضعیت نامشخص»
        title2 = QtWidgets.QLabel("اقدامات با وضعیت نامشخص")
        f2 = title2.font(); f2.setPointSize(13); f2.setBold(True)
        title2.setFont(f2)
        title2.setAlignment(Qt.AlignRight)
        title2.setLayoutDirection(Qt.RightToLeft)
        root.addWidget(title2)

        self.list_unknown = RTLListWidget()
        self.list_unknown.setObjectName("ListCard")
        root.addWidget(self.list_unknown, 1)

        # استایل — بدون property جعلی
        self.setStyleSheet("""
        #TaxApp2Root { 
            background: transparent; 
        }
        #TaxApp2Root QLabel { 
            color:#F5F5F5; 
        }

        #NavTinyBtn {
            border:1px solid #383838; border-radius:10px; background:#2C2E33;
            color:#F5F5F5; padding:0 8px; min-height:30px;
        }
        #NavTinyBtn:hover { border-color:#FFFFFF; }

        #DayCard {
            border:1px solid #383838; border-radius:16px; background:#1E1E1E; color:#F5F5F5;
        }
        #DayCard[selected="true"] {
            border:2px solid #FFFFFF; background:#000000;
        }
        #DayCard QLabel { color:#F5F5F5; }

        #Badge {
            border:2px solid #FFFFFF; border-radius:11px; background:#EF4444; color:#FFFFFF;
            font-weight:700; font-size:10pt;
        }

        #ListCard {
            border:1px solid #383838; border-radius:12px; background:transparent; color:#F5F5F5;
        }

        #InfoCard {
            border:1px solid #383838; border-radius:12px; background:#1E1E1E; color:#F5F5F5;
        }

        #EditBtn {
            border:none; border-radius:17px; padding:0 14px; min-width:84px; min-height:34px;
            background:#3A86FF; color:#FFFFFF;
        }
        #EditBtn:hover { background:#3479E6; }
        #EditBtn:pressed { background:#2C68C4; }
        QTextEdit#NoteText { padding: 6px 8px; }
        QTextEdit, QPlainTextEdit { background: #2C2E33; color: #EDEDED; }
        QTextEdit#NoteText { background: #2C2E33; color: #EDEDED; }
        """)

        self.btn_prev.clicked.connect(self._nav_prev)
        self.btn_next.clicked.connect(self._nav_next)

    # ---------- Data ----------
    def _guess_project_root(self):
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.dirname(here)

    def _load_data(self):
        """Load activities from database using tax_logic."""
        try:
            items = load_activities()
        except Exception as e:
            items = []
            try:
                QtWidgets.QMessageBox.critical(self, "خطا", f"خواندن اقدامات ناموفق بود: {e}")
            except Exception:
                pass
            return
        self.data = items
        try:
            self._records_cache = list(items)
        except Exception:
            self._records_cache = []
        self.actions_by_date = self._build_actions_map(items)
        self.overdue_actions = self._compute_overdue_actions(items)
        return

    def _build_actions_map(self, data_list):
        by_date = {}
        for idx, item in enumerate(data_list):
            if not isinstance(item, dict):
                continue
            comp   = item.get('company_name', '—')
            status = item.get('status', '—')
            rid    = item.get('id') or item.get('__id')
            raw    = item.get('last_action_date', '')
            values = raw if isinstance(raw, list) else [raw]
            for s in values:
                s_std = parse_jalali_date_str(s)
                if not s_std:
                    continue
                by_date.setdefault(s_std, []).append({
                    'id': rid,
                    'company_name': comp,
                    'status': status,
                    'last_action_date': s_std,
                    'index': idx
                })
        return by_date

    def _compute_overdue_actions(self, data_list):
        ty, tm, td = gregorian_to_jalali(self.today.year, self.today.month, self.today.day)
        today_j = (ty, tm, td)
        items = []
        for idx, item in enumerate(data_list):
            if not isinstance(item, dict):
                continue
            comp   = item.get('company_name', '—')
            status = item.get('status', '—')
            if (status or "").strip() == "مختومه":
                continue
            rid    = item.get('id') or item.get('__id')
            raw    = item.get('last_action_date', '')
            candidates = raw if isinstance(raw, list) else [raw]
            parsed = []
            for s in candidates:
                s_std = parse_jalali_date_str(s)
                if s_std:
                    jy, jm, jd = map(int, s_std.split('/'))
                    parsed.append(((jy, jm, jd), s_std))
            if not parsed:
                continue
            (jy, jm, jd), s_std = max(parsed, key=lambda t: t[0])
            if (jy, jm, jd) < today_j:
                items.append({
                    'id': rid,
                    'company_name': comp,
                    'status': status,
                    'last_action_date': s_std,
                    'index': idx,
                    'jtuple': (jy, jm, jd)
                })
        items.sort(key=lambda x: x['jtuple'], reverse=True)
        return items

    def _maybe_reload_sheet(self):
        try:
            self._load_data()
            self._rebuild_ui_state()
        except Exception:
            pass

    # ---------- Helpers ----------
    def _add_empty_row(self, target_list: RTLListWidget):
        item = QtWidgets.QListWidgetItem("موردی یافت نشد")
        f = item.font()
        f.setPointSize(18)
        f.setBold(True)
        item.setFont(f)
        item.setTextAlignment(Qt.AlignCenter)
        item.setSizeHint(QtCore.QSize(0, 64))
        item.setFlags(Qt.ItemIsEnabled)
        target_list.addItem(item)

    def _apply_editor_window_size(self, win: QtWidgets.QWidget):
        """الزام اندازهٔ ادیت‌ویندو مطابق اپ۳."""
        try:
            win.setMinimumSize(EDITOR_MIN_W, EDITOR_MIN_H)
            win.setMaximumSize(EDITOR_MAX_W, EDITOR_MAX_H)
            sz = win.size()
            if sz.width() < EDITOR_MIN_W or sz.height() < EDITOR_MIN_H:
                win.resize(EDITOR_MIN_W, EDITOR_MIN_H)
        except Exception:
            pass

    # ---------- UI State ----------
    def _rebuild_ui_state(self):
        jy, jm, jd = gregorian_to_jalali(self.selected_date.year, self.selected_date.month, self.selected_date.day)
        self.lbl_month.setText(f"{JALALI_MONTHS[jm-1]} {to_persian_digits(jy)}")

        for i, card in enumerate(self.cards):
            g_date = self.week_anchor + datetime.timedelta(days=i)
            jy, jm, jd = gregorian_to_jalali(g_date.year, g_date.month, g_date.day)
            jkey = f"{jy:04d}/{jm:02d}/{jd:02d}"
            cnt = len(self.actions_by_date.get(jkey, []))
            card.set_date_number(jd)
            card.set_count(cnt)
            card.set_selected(g_date == self.selected_date)

        self._fill_actions_for_selected_day()
        self._fill_unknown_list()

    def _fill_actions_for_selected_day(self):
        jy, jm, jd = gregorian_to_jalali(self.selected_date.year, self.selected_date.month, self.selected_date.day)
        jkey = f"{jy:04d}/{jm:02d}/{jd:02d}"
        acts = list(self.actions_by_date.get(jkey, []))

        self.list_actions.clear()
        if not acts:
            self._add_empty_row(self.list_actions)
            return

        for a in acts:
            comp = a.get('company_name', '—')
            status = a.get('status', '—')
            date = a.get('last_action_date', '—')
            it = QtWidgets.QListWidgetItem()
            w = ActionCardWidget(comp, status, date, with_edit=False)
            w.setLayoutDirection(Qt.RightToLeft)
            it.setSizeHint(QtCore.QSize(0, 90))
            self.list_actions.addItem(it)
            self.list_actions.setItemWidget(it, w)

    def _fill_unknown_list(self):
        self.list_unknown.clear()
        items = self.overdue_actions
        if not items:
            self._add_empty_row(self.list_unknown)
            return

        for a in items:
            comp = a.get('company_name', '—')
            status = a.get('status', 'نامشخص')
            date = a.get('last_action_date', '—')
            rec_id = a.get('id')
            idx = a.get('index')

            it = QtWidgets.QListWidgetItem()
            w = ActionCardWidget(
                comp, status, date,
                with_edit=True,
                on_edit=lambda rid=rec_id, ix=idx: self.open_edit_dialog(rec_id=rid, idx=ix),
                on_next_reminder=lambda rid=rec_id, ix=idx: self._set_next_reminder(rec_id=rid, idx=ix)
            )
            w.setLayoutDirection(Qt.RightToLeft)
            it.setSizeHint(QtCore.QSize(0, 90))
            self.list_unknown.addItem(it)
            self.list_unknown.setItemWidget(it, w)

    # ---------- Events ----------
    def _on_day_clicked(self, idx):
        self.selected_date = self.week_anchor + datetime.timedelta(days=idx)
        self._rebuild_ui_state()

    def _nav_prev(self):
        idx = (self.selected_date.weekday() - 5) % 7
        self.week_anchor -= datetime.timedelta(days=7)
        self.selected_date = self.week_anchor + datetime.timedelta(days=idx)
        self._rebuild_ui_state()

    def _nav_next(self):
        idx = (self.selected_date.weekday() - 5) % 7
        self.week_anchor += datetime.timedelta(days=7)
        self.selected_date = self.week_anchor + datetime.timedelta(days=idx)
        self._rebuild_ui_state()

    # ---------- External editor ----------
    def open_edit_dialog(self, rec_id=None, idx=None):
        """باز کردن فقط EditWindow (DB-backed)."""
        rid = str(rec_id or "").strip()
        if not rid:
            QtWidgets.QMessageBox.critical(self, "خطا", "این رکورد شناسه (id) ندارد.")
            return

        try:
            try:
                from ui import edit_window as ew
            except Exception:
                import edit_window as ew

            creator = getattr(ew, "EditWindow", None)
            if creator is None:
                raise ImportError("EditWindow not found in edit_window.py")

            # بساز (top-level) تا ظاهر خودش را حفظ کند
            w = None
            try:
                # Try with record_id only (DB-backed version)
                w = creator(record_id=rid, parent=None)
            except TypeError:
                # تلاش برای امضاهای متفاوت سازنده
                for make in (
                    lambda: creator(rid),
                    lambda: creator(record_id=rid),
                ):
                    try:
                        w = make()
                        break
                    except TypeError:
                        w = None
                        continue

            if w is None:
                raise RuntimeError("سازندهٔ EditWindow شناخته نشد.")

            # فقط روی همین پنجره QSS را اعمال کن (scoped)
            try:
                if hasattr(ew, "QSS_PATH") and os.path.exists(ew.QSS_PATH):
                    with open(ew.QSS_PATH, "r", encoding="utf-8") as _f:
                        qss = _f.read()
                    try:
                        w.setObjectName("EditWindowRoot")
                    except Exception:
                        pass
                    w.setStyleSheet(qss)
            except Exception:
                pass

            # --- FIX: ویرایشگر را کامل RTL و فارسی کن ---
            try:
                w.setLayoutDirection(Qt.RightToLeft)
                w.setLocale(QtCore.QLocale(QtCore.QLocale.Persian, QtCore.QLocale.Iran))
                for child in w.findChildren(QtWidgets.QWidget):
                    child.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass
            # --- END FIX ---

            # --- نمایش: مودال کامل مثل اپ۳ + اندازهٔ هماهنگ ---
            parent_win = self.window()

            def _make_app_modal(dlg: QtWidgets.QDialog):
                dlg.setWindowModality(Qt.ApplicationModal)  # قفل کل اپ
                dlg.setModal(True)
                try:
                    dlg.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
                except Exception:
                    pass

            try:
                if isinstance(w, QtWidgets.QDialog):
                    try:
                        w.setParent(parent_win)
                    except Exception:
                        pass
                    self._apply_editor_window_size(w)   # اندازه مثل اپ۳
                    _make_app_modal(w)
                    w.exec()  # بلاک تا بسته شود
                else:
                    # اگر QWidget عادی است، داخل یک دیالوگ مودال بگذار
                    shell = QtWidgets.QDialog(parent_win)
                    shell.setObjectName("EditDialogShell")
                    try:
                        shell.setWindowTitle(getattr(w, "windowTitle", lambda: None)() or "ویرایش")
                    except Exception:
                        shell.setWindowTitle("ویرایش")
                    lay = QtWidgets.QVBoxLayout(shell)
                    lay.setContentsMargins(0, 0, 0, 0)
                    lay.addWidget(w)  # reparent می‌شود
                    # رشد درست محتوا
                    try:
                        w.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
                    except Exception:
                        pass
                    self._apply_editor_window_size(shell)   # اندازه مثل اپ۳
                    _make_app_modal(shell)
                    shell.exec()
            except Exception:
                # فالبک نهایی
                try:
                    self._apply_editor_window_size(w)
                    w.show()
                except Exception:
                    pass

        except Exception as e:
            # فالبک: اجرا به عنوان پردازهٔ جدا
            try:
                here = os.path.dirname(os.path.abspath(__file__))
                path = os.path.join(here, "ui", "edit_window.py")
                if not os.path.exists(path):
                    path = os.path.join(here, "edit_window.py")
                if os.path.exists(path):
                    QtWidgets.QMessageBox.information(self, "توجه", "ویرایشگر در یک پردازهٔ جدا باز می‌شود.")
                    subprocess.Popen([sys.executable, path,
                                      "--record-id", rid,
                                      "--spreadsheet-id", GSHEET_ID,
                                      "--sheet", GSHEET_WORKSHEET,
                                      "--sa-json", GOOGLE_CREDS_JSON],
                                     cwd=here)
                else:
                    QtWidgets.QMessageBox.critical(self, "خطا", "edit_window.py پیدا نشد.")
            except Exception as e2:
                QtWidgets.QMessageBox.critical(self, "خطا", "باز کردن ویرایشگر ناموفق بود: " + str(e2))

        # رفرش دیتا بعد از بستن
        try:
            self._load_data()
            self._rebuild_ui_state()
        except Exception:
            pass

    def _set_next_reminder(self, rec_id=None, idx=None):
        rid = str(rec_id or "").strip()
        if not rid:
            QtWidgets.QMessageBox.critical(self, "خطا", "این رکورد شناسه (id) ندارد.")
            return

        # مقدار اولیه از ردیف موجود (robust)
        initial = ""
        try:
            records = getattr(self, "_records_cache", None) or getattr(self, "data", [])
            for rec in records:
                if str(rec.get("id","")).strip() == rid:
                    val = rec.get("last_action_date", "")
                    if isinstance(val, list):
                        val = (val[-1] if val else "")
                    initial = str(val or "").strip()
                    break
        except Exception:
            pass

        dlg = NextReminderDialog(initial_value=initial, parent=self)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        new_val = (dlg.get_value() or "").strip()
        if not new_val or new_val == initial:
            return

        # یادداشت‌های واردشده در دیالوگ
        try:
            notes = dlg.get_notes()
        except Exception:
            notes = []

        try:
            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        except Exception:
            pass
        try:
            self._update_last_action_date_in_sheet(rid, new_val, notes)
            QtWidgets.QMessageBox.information(self, "ثبت شد", f"تاریخ یادآوری بعدی روی {new_val} ذخیره شد.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", f"ثبت یادآوری ناموفق بود:\n{e}")
        finally:
            try:
                QtWidgets.QApplication.restoreOverrideCursor()
            except Exception:
                pass

        # رفرش لیست‌ها
        try:
            self._load_data()
            self._rebuild_ui_state()
        except Exception:
            pass

    def _update_last_action_date_in_sheet(self, rec_id: str, date_str: str, notes: list | None = None):
        """Update last_action_date in database and append notes using tax_logic."""
        try:
            # Find activity by ID
            activity = next((a for a in self.data if str(a.get('id', '')) == str(rec_id)), None)
            if not activity:
                raise RuntimeError("فعالیتی با این id پیدا نشد.")
            
            # Update activity fields
            activity['last_action_date'] = date_str
            
            # Merge new notes with existing ones
            new_notes = [str(x).strip() for x in (notes or []) if str(x).strip()]
            if new_notes:
                existing_notes = activity.get('reminder_notes', [])
                if isinstance(existing_notes, str):
                    try:
                        existing_notes = json.loads(existing_notes)
                    except Exception:
                        existing_notes = [existing_notes] if existing_notes else []
                elif not isinstance(existing_notes, list):
                    existing_notes = []
                
                # Merge and deduplicate
                merged = list(existing_notes) if isinstance(existing_notes, list) else [existing_notes]
                merged.extend(new_notes)
                seen = set()
                unique_notes = []
                for n in merged:
                    n_str = str(n).strip()
                    if n_str and n_str not in seen:
                        seen.add(n_str)
                        unique_notes.append(n_str)
                
                activity['reminder_notes'] = unique_notes
            
            # Save to database
            save_activity(activity)
        except Exception as e:
            raise RuntimeError(f"ذخیره یادآوری ناموفق بود: {e}")


# ----------- Alias برای سازگاری با لانچرهای قدیمی -----------
AppWidget = App2Widget