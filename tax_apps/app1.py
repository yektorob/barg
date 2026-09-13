
import os
import sys
import json
import shutil
import datetime
import uuid
import jdatetime
import base64

from PySide6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QPushButton, QMessageBox,
    QLabel, QHBoxLayout, QTextEdit, QFrame, QFileDialog,
    QListWidget, QListWidgetItem, QRadioButton, QButtonGroup,
    QGroupBox, QComboBox, QScrollArea, QDialog, QSizePolicy, QStyle, QApplication, QAbstractSpinBox, QCheckBox
)
from PySide6 import QtGui, QtCore
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QRegularExpressionValidator, QPalette, QColor, QPainter, QPixmap, QIcon 
from PySide6.QtCore import QRegularExpression, Qt, QSize, QEvent

# پنل‌ها (PySide6)
from widgets.bodavi_panel import BodaviPanel
from widgets.tajdid_panel import TajdidPanel

# ===== مسیرها =====
HERE          = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT  = os.path.dirname(HERE)
STORAGE_FILE  = os.path.join(PROJECT_ROOT, 'companies.json')  # Legacy; using DB now
SETTINGS_FILE = os.path.join(PROJECT_ROOT, 'settings.json')
UPLOAD_ROOT = r"D:\uploads"
os.makedirs(UPLOAD_ROOT, exist_ok=True)

# ===== Import DB logic (replaces Google Sheets) =====
try:
    from tax_apps import tax_logic
except (ImportError, ModuleNotFoundError):
    # Fallback if tax_logic not available (development mode)
    tax_logic = None

# ===== آیکون نوتیف (SVG Base64) =====
SVG_BELL_B64 = b"""PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciICB2aWV3Qm94PSIwIDAgNTAgNTAiIHdpZHRoPSIxMDBweCIgaGVpZ2h0PSIxMDBweCI+PHBhdGggZmlsbD0iI2ZmOTYwMCIgZD0iTTQzLjc1MiwzNi4yMTdjLTAuMDYyLTAuMTk2LTAuMTM5LTAuMzkzLTAuMjMyLTAuNTk0Yy0wLjU5OS0xLjI5NC0xLjQxLTIuNDgxLTIuMDQxLTMuNzU5IGMtMS4zODEtMi43OTctMS4wMTItNS45ODQtMS40NC04Ljk5OGMtMC40MS0yLjg4My0xLjE2My01Ljc2OC0yLjQxMi04LjQwNmMtMS4xMTYtMi4zNTgtMi44MTYtNC41NTktNS4xOTYtNS43MzYgYy0xLjM3OC0wLjY4MS0yLjg5OC0xLjEzNi00LjQ1NS0xLjM4MWMwLTAuMDA1LDAuMDAxLTAuMDA5LDAtMC4wMTRDMjcuODcxLDYuMDM5LDI3LjMsNC44NTQsMjYuMjUsNC4wNzcgYy0wLjkyNy0wLjY4Ny0yLjI3LTAuOTAxLTMuMzUzLTAuNDgyYy0xLjE4NiwwLjQ1OS0yLjAwNiwxLjU0My0yLjIxOCwyLjc5Yy0wLjA2OCwwLjM5OC0wLjA3OCwwLjc5Mi0wLjA0NywxLjE4IGMtMS45MzIsMC41NDMtMy43MjgsMS41ODktNS4xNTQsMy4wMDljLTIuNDc3LDIuNDY2LTMuNzA1LDUuNzM4LTQuMTI0LDkuMTU1Yy0wLjQyOSwzLjQ5Ny0wLjA5NSw3LjA5NS0xLjA2MywxMC41MTggYy0wLjQ1NiwxLjYxMS0xLjI0NywyLjk0Ny0yLjI5NCw0LjIzOGMtMC45NDYsMS4xNjUtMi4xMSwyLjYwNi0xLjk4OCw0LjIxM2MwLjExNywxLjU0NSwxLjQwMSwyLjA0LDIuNzY0LDIuMTQ1IGMwLjE5NywwLjAzMiwwLjM5MywwLjA1OSwwLjU4MiwwLjA4OGMxLjM5MywwLjIxNiwyLjc5OCwwLjMzMiw0LjIwNywwLjM3NWMxLjMyNywwLjA0MSwyLjY1NCwwLjAyOCwzLjk4MS0wLjAwOSBjMC4yOTMsMi4yMTUsMS40NzksNC4zNDcsMy40OTQsNS4zMmMzLjIxNCwxLjU1Miw3LjM1OC0wLjMzOSw5LjA1NC0zLjI2OGMwLjQ4Mi0wLjgzMiwwLjc5MS0xLjczOSwwLjkzNy0yLjY3MiBjMC4wMzUtMC4wMDEsMC4wNy0wLjAwMywwLjEwNS0wLjAwN2MyLjkzOS0wLjA3Myw1Ljg3MSwwLjAxNyw4LjgwOCwwLjAwN2MwLjg3Ni0wLjAwMywxLjc4OC0wLjEyMywyLjU1My0wLjUxNiBjMC4wNy0wLjAyNCwwLjEzNS0wLjA3MiwwLjIwMy0wLjExOWMwLjM0My0wLjIwOCwwLjY1NC0wLjQ3MSwwLjkwNi0wLjgyMkM0NC4yNDcsMzguMzIxLDQ0LjM0NywzNy4xMjMsNDMuNzUyLDM2LjIxN3oiLz48L3N2Zz4="""

def svg_icon_from_base64(b64: bytes, size: int = 22) -> QIcon:
    data = base64.b64decode(b64)
    renderer = QSvgRenderer(data)
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    return QIcon(pm)

# ===== کمکی =====
def validate_jalali(s: str) -> bool:
    try:
        jdatetime.datetime.strptime(s, "%Y/%m/%d")
        return True
    except:
        return False
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
# ─────────────────────────────────────────────────────────────────────────────
# اتومات محو/پررنگ کردن لیبل‌ها وقتی فیلد Disable/Enable می‌شود
class _LabelDimmer(QtCore.QObject):
    def __init__(self, form: QFormLayout):
        super().__init__()
        self.form = form
        self.map = {}  # field -> label

    def watch(self, field: QWidget):
        lbl = self.form.labelForField(field)
        if lbl:
            self.map[field] = lbl
            field.installEventFilter(self)
            self._sync(field)

    def _sync(self, field: QWidget):
        lbl = self.map.get(field)
        if lbl:
            lbl.setEnabled(field.isEnabled())

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.EnabledChange:
            self._sync(obj)
        return super().eventFilter(obj, ev)

# ===== ویجت یادداشت داینامیک (ظاهر جدید) =====
class DynamicNotesWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.entries = []

        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(8)

        # دکمه افزودن (آیکن + متن)
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(6)

        self.btn_add = QPushButton("افزودن یادداشت")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_add.clicked.connect(lambda: self.add_note(""))
        top.addWidget(self.btn_add, 0, Qt.AlignRight)
        top.addStretch()
        self.v.addLayout(top)

        # لیست کارت‌های یادداشت
        self.list_v = QVBoxLayout()
        self.list_v.setContentsMargins(0, 0, 0, 0)
        self.list_v.setSpacing(8)
        self.v.addLayout(self.list_v)

    def add_note(self, text: str):
        card = QFrame()
        card.setObjectName("NoteCard")
        h = QHBoxLayout(card)
        h.setContentsMargins(8, 8, 8, 8)
        h.setSpacing(8)

        te = QTextEdit()
        te.setObjectName("NoteText")
        te.setFixedHeight(64)
        te.setPlainText(text)

        btn_del = QPushButton()
        btn_del.setObjectName("DelNote")
        btn_del.setFixedSize(34, 34)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setToolTip("حذف یادداشت")
        # آیکون حذف استاندارد
        btn_del.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        btn_del.clicked.connect(lambda _, c=card: self.remove_note(c))

        h.addWidget(te, 1)
        h.addWidget(btn_del, 0, Qt.AlignTop)

        self.list_v.addWidget(card)
        self.entries.append((card, te))

    def remove_note(self, card: QFrame):
        for c, te in list(self.entries):
            if c is card:
                self.entries.remove((c, te))
                c.setParent(None)
                break

    def get_notes(self):
        return [te.toPlainText().strip()
                for _, te in self.entries
                if te.toPlainText().strip()]

# ===== دیالوگ تنظیمات نوتیفیکیشن =====
class NotificationSettingsDialog(QDialog):
    def __init__(self, parent=None, settings_path=SETTINGS_FILE):
        super().__init__(parent)
        self.setWindowTitle("تنظیم نوتیفیکیشن")
        self.settings_path = settings_path
        self.settings = {}
        if os.path.exists(settings_path):
            try:
                self.settings = json.load(open(settings_path, 'r', encoding='utf-8')) or {}
            except:
                self.settings = {}

        form = QFormLayout(self)

        self.days = QSpinBox()
        self.days.setRange(0, 365)
        self.days.setSuffix(" روز")
        self.days.setToolTip("چند روز قبل از موعد نوتیف ارسال شود")
        self.days.setButtonSymbols(QAbstractSpinBox.PlusMinus)  # ← Plus/Minus
        if 'notify_days' in self.settings:
            self.days.setValue(int(self.settings['notify_days']))
        form.addRow("نوتیف چند روز قبل:", self.days)

        self.mode = QComboBox()
        # گزینه‌ها به ترتیب موردنظر: یک بار / دوبار / روزانه
        self.mode.addItems(["یک بار", "دوبار", "روزانه"])
        self.mode.setToolTip("حالت ارسال نوتیف: یک بار / دوبار / روزانه")
        m2t = {'once': "یک بار", 'twice': "دوبار", 'daily': "روزانه"}
        if 'notify_mode' in self.settings:
            target = m2t.get(self.settings['notify_mode'], "روزانه")
            self.mode.setCurrentIndex(self.mode.findText(target))
        else:
            self.mode.setCurrentText("روزانه")

        # نمایش کمبو در فرم
        form.addRow("حالت نوتیف:", self.mode)

        btns = QHBoxLayout()
        btn_save = QPushButton("ذخیره")
        btn_save.clicked.connect(self.on_save)
        btns.addWidget(btn_save)
        form.addRow(btns)

        self.parent_ref = parent

    def on_save(self):
        t2m = {"یک بار": "once", "یک‌بار": "once", "یکبار": "once", "دوبار": "twice", "دو بار": "twice", "روزانه": "daily"}
        out = {}
        if self.days.value() != 0:
            out['notify_days'] = self.days.value()
        sel = self.mode.currentText()
        if sel in t2m:
            out['notify_mode'] = t2m[sel]

        with open(self.settings_path, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=4)

        if self.parent_ref:
            self.parent_ref.global_settings = out

        QMessageBox.information(self, "ذخیره", "تنظیمات ذخیره شد")
        self.accept()

# ===== دیالوگ‌ها (منطق تو حفظ شده) =====
class NextReminderDialog(QDialog):
    def __init__(self, parent=None, status=""):
        super().__init__(parent)
        self.status = status
        self.setWindowTitle("تاریخ یادآوری بعدی")
        self.resize(360, 340)
        layout = QFormLayout(self)

        title = "تاریخ جلسه دوم" if status else "تاریخ یادآوری بعدی"
        self.date = QLineEdit()
        self.date.setInputMask("0000/00/00;_")
        layout.addRow(title + ":", self.date)

        layout.addRow(QLabel("یادداشت‌های یادآوری:"))
        self.notes = DynamicNotesWidget()
        layout.addRow(self.notes)

        h = QHBoxLayout()
        ok = QPushButton("تأیید")
        cancel = QPushButton("انصراف")
        ok.clicked.connect(self.on_ok)
        cancel.clicked.connect(self.reject)
        h.addWidget(ok)
        h.addWidget(cancel)
        layout.addRow(h)

    def on_ok(self):
        dtxt = self.date.text().strip()
        if not validate_jalali(dtxt):
            QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ شمسی معتبر وارد کنید")
            return
        d = jdatetime.datetime.strptime(dtxt, "%Y/%m/%d").date()
        if d < jdatetime.date.today():
            QMessageBox.warning(self, "تاریخ نامعتبر", "تاریخ گذشته مجاز نیست")
            return
        self.accept()

    def get_data(self):
        return {
            'next_date': self.date.text().strip(),
            'reminder_notes': self.notes.get_notes(),
            'status': self.status
        }

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
        v.addWidget(QLabel("می‌خواهید پرونده مختومه شود؟"))
        self.rb_yes = QRadioButton("بله")
        self.rb_no = QRadioButton("خیر")
        self.bg = QButtonGroup(self)
        self.bg.addButton(self.rb_yes)
        self.bg.addButton(self.rb_no)
        v.addWidget(self.rb_yes)
        v.addWidget(self.rb_no)
        btn = QPushButton("تأیید")
        btn.clicked.connect(self.on_ok)
        v.addWidget(btn)

    def on_ok(self):
        if not (self.rb_yes.isChecked() or self.rb_no.isChecked()):
            QMessageBox.warning(self, "اجباری", "لطفاً یک گزینه انتخاب کنید")
            return
        self.accept()

    def get_decision(self):
        return self.rb_yes.isChecked()

# ===== پنجره اصلی (تب اول داشبورد) =====
class MainWindow(QTabWidget):
    def __init__(self, parent=None):          # ← parent بپذیر
        super().__init__(parent)               # ← parent بده به سوپر
        self.setWindowTitle("مدیریت پرونده")
        self.resize(860, 1000)

        # تنظیمات (بدون پیش‌فرض؛ اگر فایل خالی بود -> {})
        self.global_settings = self.load_settings()
        self._init_ui()

        # مخفی کردن tabBar داخلی تا «پرونده جدید» دیده نشود
        self.tabBar().hide()

        # ===== اعمال استایل عباسپور + اووررایدها =====
        self._apply_abbaspoor_style()

        # اطمینان از PlusMinus و سرعت برای همه SpinBoxها
        for sp in self.findChildren(QSpinBox):
            sp.setButtonSymbols(QAbstractSpinBox.PlusMinus)
            sp.setAccelerated(True)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                return json.load(open(SETTINGS_FILE, 'r', encoding='utf-8')) or {}
            except:
                pass
        return {}

    # ---------- Helpers: آپلود لیست با دکمه حذف ----------


    # ---------- بازسازی فرم بعد از ثبت موفق ----------
    def reload_form(self):
        """کل تب فرم را حذف و دوباره ایجاد می‌کند تا همه‌چیز به حالت اولیه برگردد."""
        try:
            # حذف همه تب‌های موجود
            for i in reversed(range(self.count())):
                w = self.widget(i)
                self.removeTab(i)
                try:
                    w.setParent(None)
                except Exception:
                    pass
                try:
                    w.deleteLater()
                except Exception:
                    pass
        except Exception:
            pass
        # ایجاد دوبارهٔ UI
        self._init_ui()

    def _add_file_item(self, listw: QListWidget, path: str, bucket: str):
        item = QListWidgetItem()
        widget = QWidget()
        h = QHBoxLayout(widget)
        h.setContentsMargins(8, 4, 8, 4)
        h.setSpacing(8)

        name = os.path.basename(path)
        lbl = QLabel(name)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

        btn = QPushButton()
        btn.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        btn.setFixedSize(32, 28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip("حذف فایل")
        def _remove():
            row = listw.row(item)
            if row >= 0:
                listw.takeItem(row)

            if bucket == "upload":
                try:
                    self.uploaded_files.remove(path)
                except ValueError:
                    pass
            elif bucket == "petition":
                try:
                    self.petition_uploaded_files.remove(path)
                except ValueError:
                    pass
            elif bucket == "report":
                try:
                    self.report_uploaded_files.remove(path)
                except ValueError:
                    pass
            # حذف فایل از دیسک اختیاری است؛ فعلاً نمی‌زنیم
        btn.clicked.connect(_remove)

        h.addWidget(lbl, 1)
        h.addWidget(btn, 0, Qt.AlignRight)

        item.setSizeHint(QSize(260, 36))
        listw.addItem(item)
        listw.setItemWidget(item, widget)

    def _make_upload_row(self, title: str, which: str):
        # which in {"upload","petition","report"}
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        if which == "upload":
            btn_text = "آپلود فایل‌ها"
        elif which == "petition":
            btn_text = "آپلود فایل‌های لایحه"
        else:  # which == "report"
            btn_text = "آپلود فایل‌های گزارش رسیدگی"

        btn = QPushButton(btn_text)
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn.setCursor(Qt.PointingHandCursor)

        lst = QListWidget()
        lst.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lst.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        lst.setFixedHeight(84)
        lst.setMinimumWidth(280)

        if which == "upload":
            self.upload_btn = btn
            self.upload_btn.setEnabled(False)
            self.upload_list = lst
            self.uploaded_files = []
            btn.clicked.connect(self._upload_files)
        elif which == "petition":
            self.petition_upload_btn = btn
            self.petition_upload_btn.setEnabled(False)
            self.petition_upload_list = lst
            self.petition_uploaded_files = []
            btn.clicked.connect(self._upload_petition_files)
        else:  # report
            self.report_upload_btn = btn
            self.report_upload_btn.setEnabled(False)
            self.report_upload_list = lst
            self.report_uploaded_files = []
            btn.clicked.connect(self._upload_report_files)

        h.addWidget(btn, 0, Qt.AlignRight)
        h.addWidget(lst, 1)

        return (title, row)

    def _init_ui(self):
        tab = QWidget()
        tab.setObjectName("AbbaspoorPage")
        self.addTab(tab, "پرونده جدید")  # عنوان مهم نیست چون tabBar مخفی است

        form = QFormLayout()
        form.setSpacing(8)
        form.setHorizontalSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop | Qt.AlignRight)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # --- دکمه نوتیف داخل خود فرم (بالای فرم، سمت راست) ---
        topbar_w = QWidget()
        topbar = QHBoxLayout(topbar_w)
        topbar.setContentsMargins(0, 0, 0, 0)
        topbar.setSpacing(0)

        self.btn_notif = QPushButton()
        self.btn_notif.setObjectName("NotifBtn")
        self.btn_notif.setIcon(svg_icon_from_base64(SVG_BELL_B64, 20))
        self.btn_notif.setIconSize(QSize(20, 20))
        self.btn_notif.setFixedSize(36, 36)
        self.btn_notif.setCursor(Qt.PointingHandCursor)
        self.btn_notif.setToolTip("تنظیم نوتیفیکیشن")
        self.btn_notif.setFlat(True)
        self.btn_notif.clicked.connect(self._open_notif_dialog)

        topbar.addWidget(self.btn_notif, 0, Qt.AlignRight)
        topbar.addStretch()
        # درج به عنوان اولین ردیف فرم
        form.insertRow(0, "", topbar_w)

        # ------------------ فیلدها ------------------
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

        self.company = QLineEdit()
        form.addRow("نام شخص/شرکت*:", self.company)

        self.fiscal = QLineEdit(); self.fiscal.setMaxLength(4)
        form.addRow("سال مالی*:", self.fiscal)

        self.entry = QLineEdit(); self.entry.setInputMask("0000/00/00;_")
        form.addRow("تاریخ ورود به موسسه:", self.entry)

        
        self.case_types = ["تکلیفی", "حقوقی", "ارزش افزوده", "مالیات بر عملکرد", "مستقلات"]
        self.case_checkboxes = []
        case_wrap = QWidget(); h_case = QHBoxLayout(case_wrap); h_case.setContentsMargins(0,0,0,0)
        for label in self.case_types:
            cb = QCheckBox(label)
            self.case_checkboxes.append(cb)
            h_case.addWidget(cb)
        h_case.addStretch()
        form.addRow("نوع پرونده:", case_wrap)

        # رفرنس مستقیم به چک‌باکس‌های «ارزش افزوده» و «مالیات بر عملکرد»
        try:
            self.cb_vat = self.case_checkboxes[self.case_types.index("ارزش افزوده")]
        except ValueError:
            self.cb_vat = None
        try:
            self.cb_perf = self.case_checkboxes[self.case_types.index("مالیات بر عملکرد")]
        except ValueError:
            self.cb_perf = None

        # تغییر نوع پرونده روی فیلدهای وابسته (مبالغ مالیات/جریمه) اثر می‌گذارد
        if self.cb_vat is not None:
            self.cb_vat.toggled.connect(self._on_case_type_changed)
        if self.cb_perf is not None:
            self.cb_perf.toggled.connect(self._on_case_type_changed)

        self.submit_date = QLineEdit(); self.submit_date.setInputMask("0000/00/00;_")
        form.addRow("تاریخ ارائه اسناد و مدارک:", self.submit_date)
        self.deadline_days = QSpinBox(); self.deadline_days.setRange(0, 365)
        self.deadline_days.setSuffix(" روز")
        self.deadline_days.setToolTip("چند روز مهلت برای ارائه وجود دارد؟")
        self.deadline_days.setButtonSymbols(QAbstractSpinBox.PlusMinus)  # ← Plus/Minus
        form.addRow("چند روز مهلت برای ارائه هست:", self.deadline_days)
        self.due_date = QLineEdit(); self.due_date.setReadOnly(True)
        form.addRow("مهلت ارائه اسناد و مدارک:", self.due_date)
        self.submit_date.textChanged.connect(self._update_due)
        self.deadline_days.valueChanged.connect(self._update_due)

        self.status_texts = ["ارائه شد", "ارائه نشد"]
        self.group_status = QButtonGroup(self)
        status_wrap = QWidget(); h_status = QHBoxLayout(status_wrap); h_status.setContentsMargins(0,0,0,0)
        for idx, text in enumerate(self.status_texts):
            rb = QRadioButton(text)
            self.group_status.addButton(rb, idx)
            h_status.addWidget(rb)
        h_status.addStretch()
        form.addRow("وضعیت ارائه اسناد:", status_wrap)
        self.group_status.idClicked.connect(self._on_status_changed)

        self.upload_date = QLineEdit(); self.upload_date.setInputMask("0000/00/00;_"); self.upload_date.setEnabled(False)
        form.addRow("تاریخ ارائه مدارک:", self.upload_date)

        # ردیف آپلود مدارک (دکمه و لیست کنار هم)
        label, row = self._make_upload_row("", "upload")
        form.addRow("فایل‌های مدارک:", row)

        self.rb_has_ass_yes = QRadioButton("بله"); self.rb_has_ass_no = QRadioButton("خیر")
        self.group_has_ass = QButtonGroup(self); self.group_has_ass.addButton(self.rb_has_ass_yes, 1); self.group_has_ass.addButton(self.rb_has_ass_no, 0)
        ass_wrap = QWidget(); h_ass = QHBoxLayout(ass_wrap); h_ass.setContentsMargins(0,0,0,0)
        h_ass.addWidget(self.rb_has_ass_yes); h_ass.addWidget(self.rb_has_ass_no); h_ass.addStretch()
        form.addRow("برگه تشخیص دارد؟", ass_wrap)
        for rb in (self.rb_has_ass_yes, self.rb_has_ass_no):
            rb.setEnabled(False)
        self.group_has_ass.idClicked.connect(self._on_assessment_changed)

        # فیلدهای دوره‌ای مخصوص پرونده‌های «ارزش افزوده» (۴ دوره، قبل از مبلغ مالیات)
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

        self.penalty_amount = QLineEdit()
        # اجازه فقط رقم و کاما؛ وضعیت‌های میانی تایپ هم رد نشوند
        self.penalty_amount.setValidator(QRegularExpressionValidator(QRegularExpression(r'^[\d,]{0,18}$'), self.penalty_amount))
        # فرمت‌کردن حین تایپ
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
        self.assess_date = QLineEdit(); self.assess_date.setInputMask("0000/00/00;_"); self.assess_date.setEnabled(False)
        form.addRow("تاریخ ابلاغ برگه تشخیص:", self.assess_date)
        self.assess_deadline = QLineEdit(); self.assess_deadline.setReadOnly(True); self.assess_deadline.setEnabled(False)
        form.addRow("مهلت اعتراض برگه تشخیص:", self.assess_deadline)
        self.assess_date.textChanged.connect(self._update_assess_deadline)

        self.rb_report_yes = QRadioButton("بله"); self.rb_report_no = QRadioButton("خیر")
        self.group_report = QButtonGroup(self); self.group_report.addButton(self.rb_report_yes, 1); self.group_report.addButton(self.rb_report_no, 0)
        rep_wrap = QWidget(); h_rep = QHBoxLayout(rep_wrap); h_rep.setContentsMargins(0,0,0,0)
        h_rep.addWidget(self.rb_report_yes); h_rep.addWidget(self.rb_report_no); h_rep.addStretch()
        form.addRow("گزارش رسیدگی دارد؟", rep_wrap)
        for rb in (self.rb_report_yes, self.rb_report_no):
            rb.setEnabled(False)
        self.group_report.idClicked.connect(self._on_report_changed)
        # ردیف آپلود فایل‌های گزارش رسیدگی
        _, row_report = self._make_upload_row("", "report")
        form.addRow("فایل‌های گزارش رسیدگی:", row_report)
        self.rb_objected_yes = QRadioButton("بله"); self.rb_objected_no = QRadioButton("خیر")
        self.group_objected = QButtonGroup(self); self.group_objected.addButton(self.rb_objected_yes, 1); self.group_objected.addButton(self.rb_objected_no, 0)
        obj_wrap = QWidget(); h_obj = QHBoxLayout(obj_wrap); h_obj.setContentsMargins(0,0,0,0)
        h_obj.addWidget(self.rb_objected_yes); h_obj.addWidget(self.rb_objected_no); h_obj.addStretch()
        form.addRow("اعتراض شده؟", obj_wrap)
        for rb in (self.rb_objected_yes, self.rb_objected_no):
            rb.setEnabled(False)
        self.group_objected.idClicked.connect(self._on_objected_changed)

        self.appeal_send = QLineEdit(); self.appeal_send.setInputMask("0000/00/00;_"); self.appeal_send.setEnabled(False)
        form.addRow("تاریخ اعتراض:", self.appeal_send)
        self.appeal_send.textChanged.connect(self._on_appeal_send_change)

        # ردیف آپلود لایحه (دکمه و لیست کنار هم)
        _, row2 = self._make_upload_row("", "petition")
        form.addRow("فایل‌های لایحه:", row2)

        self.mad238_entry_date = QLineEdit(); self.mad238_entry_date.setInputMask("0000/00/00;_"); self.mad238_entry_date.setEnabled(False)
        form.addRow("تاریخ ورود به ماده ۲۳۸:", self.mad238_entry_date)
        self.mad238_agreement_deadline = QLineEdit(); self.mad238_agreement_deadline.setReadOnly(True); self.mad238_agreement_deadline.setEnabled(False)
        form.addRow("مهلت توافق ماده ۲۳۸:", self.mad238_agreement_deadline)
        self.mad238_entry_date.textChanged.connect(self._update_mad238_agreement_deadline)

        self.rb_adjust = QRadioButton("تعدیل مالیات")
        self.rb_refer = QRadioButton("ارجاع به هیأت بدوی")
        self.result_bg = QButtonGroup(self); self.result_bg.addButton(self.rb_adjust); self.result_bg.addButton(self.rb_refer)
        for rb in (self.rb_adjust, self.rb_refer): rb.setEnabled(False)
        h_res_w = QWidget(); h_res = QHBoxLayout(h_res_w); h_res.setContentsMargins(0,0,0,0)
        h_res.addWidget(self.rb_adjust); h_res.addWidget(self.rb_refer); h_res.addStretch()
        grp = QGroupBox("نتیجه توافق"); grp.setLayout(h_res)
        form.addRow(grp)

        self.bodavi = BodaviPanel(); self.bodavi.setEnabled(False)
        form.addRow(self.bodavi)
        self.rb_refer.toggled.connect(self._on_refer_toggled)
        # اتصال اعتراض بدوی به فعال/غیرفعال‌سازی پنل تجدیدنظر
        try:
            self.bodavi.obj_yes.toggled.connect(self._on_bodavi_obj_yes_toggled)
            self.bodavi.obj_no.toggled.connect(self._on_bodavi_obj_no_toggled)
        except Exception as _e:
            pass

        self.tajdid = TajdidPanel(); self.tajdid.setEnabled(False)
        form.addRow(self.tajdid)

        form.addRow(QLabel("یادداشت‌های پرونده:"), QWidget())
        self.notes_w = DynamicNotesWidget()
        form.addRow(self.notes_w)

        # دکمه ثبت شرکت (برگشت داده شد)
        self.btn_save = QPushButton("ثبت شرکت")
        self.btn_save.setProperty("variant", "primary")
        self.btn_save.clicked.connect(self._save)
        form.addRow(self.btn_save)

        # اسکرول + قاب
        container = QFrame(); container.setObjectName("AbbaspoorFrame")
        container.setLayout(form)
        container.setMaximumWidth(920)  # کمی جمع‌وجورتر
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(container)

        # وسط‌چین کردن محتوای فرم داخل اسکرول
        scroll.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        tab_layout = QVBoxLayout()
        tab_layout.addWidget(scroll)

        self.sheet_status = QLabel("آماده")
        tab_layout.addWidget(self.sheet_status)

        tab.setLayout(tab_layout)

        # لیبل دیمر
        self._ld = _LabelDimmer(form)
        for _cls in (QLineEdit, QSpinBox, QComboBox, QTextEdit):
            for w in self.findChildren(_cls):
                self._ld.watch(w)

    def _apply_abbaspoor_style(self):
        # روت برای QSS و RTL
        self.setObjectName("AbbaspoorPage")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setProperty("rtl", True)

        # لود استایل پایه
        qss_path = os.path.join(PROJECT_ROOT, 'styles', 'abbaspoor.qss')
        try:
            with open(qss_path, 'r', encoding='utf-8') as f:
                qss = f.read()
        except Exception as e:
            print("⚠️ استایل عباسپور لود نشد:", e)
            qss = ""

        # اوورراید: Disabled واضح + کارت‌ها + گرد بودن + دکمه گرد نوتیف + SpinBox
        EXTRA_QSS = """
        /* وضوح فیلدهای غیرفعال */
        QLineEdit:disabled, QAbstractSpinBox:disabled, QComboBox:disabled, QTextEdit:disabled {
            background: rgba(255,255,255,0.05);
            border: 1px dashed #2A2A2A;
            color: #8C8C8C;
        }
        QLabel:disabled { color: #777777; }

        /* گوشه‌های گرد و ارتفاع کمی جمع‌وجورتر */
        QLineEdit, QAbstractSpinBox, QComboBox, QTextEdit { min-height: 34px; border-radius: 12px; }

        /* SpinBox متن فاصله از دکمه‌ها */
        QSpinBox, QDoubleSpinBox { padding-right: 56px; }

        /* کارت یادداشت */
        QFrame#NoteCard {
            background: rgba(255,255,255,0.03);
            border: 1px solid #383838;
            border-radius: 10px;
        }
        QFrame#NoteCard:hover { border-color: #FFFFFF; }
        QTextEdit#NoteText { padding: 6px 8px; }
        QTextEdit, QPlainTextEdit { background: #2C2E33; color: #EDEDED; }
        QTextEdit#NoteText { background: #2C2E33; color: #EDEDED; }
        QPushButton#DelNote { border: 1px solid #383838; border-radius: 8px; }
        QPushButton#DelNote:hover { border-color: #FFFFFF; }

        /* دکمه نوتیف کاملاً گرد */
        QPushButton#NotifBtn {
            border: 1px solid #383838;
            background: #2C2E33;
            border-radius: 18px; /* 36x36 */
        }
        QPushButton#NotifBtn:hover { border-color: #FFFFFF; }

        /* SpinBox پله‌ها واضح‌تر و شکیل‌تر با Plus/Minus */
        QSpinBox::up-button, QDoubleSpinBox::up-button {
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 28px;
            border-left: 1px solid #383838;
            border-bottom: 1px solid #383838;
            background: #2C2E33;
            border-top-right-radius: 12px;
            margin: 0;
            padding: 0;
        }
        QSpinBox::down-button, QDoubleSpinBox::down-button {
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            width: 28px;
            border-left: 1px solid #383838;
            background: #2C2E33;
            border-bottom-right-radius: 12px;
            margin: 0;
            padding: 0;
        }
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
            background: #32343A;
            border-color: #FFFFFF;
        }
        QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
        QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {
            background: #3A3D44;
        }
        """

        self.setStyleSheet(qss + "\n" + EXTRA_QSS)

        # placeholder رنگ
        for w in self.findChildren(QLineEdit):
            wp = w.palette()
            wp.setColor(QPalette.PlaceholderText, QColor("#777777"))
            w.setPalette(wp)

    # ───── رویدادها/منطق عمومی (همان قبلی) ─────
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
        """هندلر فرمت زنده برای تمام فیلدهای عددی (مبلغ مالیات/جریمه)"""
        edit = self.sender() or self.penalty_amount

        # متن و مکان‌نما قبل از اعمال فرمت
        old_text = edit.text()
        old_cursor = edit.cursorPosition()

        new_text = self._format_with_commas(old_text)
        if new_text == old_text:
            return

        new_cursor = self._compute_new_cursor_after_format(old_text, old_cursor, new_text)
        edit.blockSignals(True)   # از لوپ جلوگیری شود
        try:
            edit.setText(new_text)
            # محدود کردن ایندکس به بازه معتبر
            new_cursor = max(0, min(len(new_text), new_cursor))
            edit.setCursorPosition(new_cursor)
        finally:
            edit.blockSignals(False)
    def _update_due(self):
        txt = self.submit_date.text().strip()
        if not validate_jalali(txt):
            self.due_date.clear()
            return
        d = jdatetime.datetime.strptime(txt, "%Y/%m/%d")
        dd = d + jdatetime.timedelta(days=self.deadline_days.value())
        self.due_date.setText(dd.strftime("%Y/%m/%d"))

    def _on_status_changed(self, id_):
        for bg in (self.group_has_ass, self.group_report, self.group_objected):
            bg.setExclusive(False)
            for btn in bg.buttons():
                btn.setChecked(False)
            bg.setExclusive(True)

        upload_ok = (id_ == 0)
        ass_ok = True

        if not upload_ok:
            self.upload_date.clear(); self.upload_date.setEnabled(False)
            self.upload_list.clear(); self.uploaded_files = []
            self.upload_btn.setEnabled(False)
        else:
            self.upload_date.setEnabled(True); self.upload_btn.setEnabled(True)

        for rb in (self.rb_has_ass_yes, self.rb_has_ass_no):
            rb.setEnabled(ass_ok)
        if not ass_ok:
            self._on_assessment_changed(0)

    def _on_assessment_changed(self, id_):
        has_ass = (id_ == 1)
        self.result_bg.setExclusive(False)
        for btn in self.result_bg.buttons():
            btn.setChecked(False); btn.setEnabled(False)
        self.result_bg.setExclusive(True)

        if has_ass:
            self.assess_date.setEnabled(True); self.assess_deadline.setEnabled(True)
            for rb in (self.rb_report_yes, self.rb_report_no, self.rb_objected_yes, self.rb_objected_no):
                rb.setEnabled(True)
        else:
            for bg in (self.group_report, self.group_objected):
                bg.setExclusive(False)
                for btn in bg.buttons():
                    btn.setChecked(False); btn.setEnabled(False)
                bg.setExclusive(True)
            self.assess_date.clear(); self.assess_date.setEnabled(False)
            self.assess_deadline.clear(); self.assess_deadline.setEnabled(False)
            self.appeal_send.clear(); self.appeal_send.setEnabled(False)
            self.petition_upload_btn.setEnabled(False)
            self.petition_upload_list.clear(); self.petition_uploaded_files = []
            self.mad238_entry_date.clear(); self.mad238_entry_date.setEnabled(False)
            self.mad238_agreement_deadline.clear(); self.mad238_agreement_deadline.setEnabled(False)
            # فیلدهای وابسته به برگه تشخیص (مبالغ مالیات/جریمه) در تابع جدا مدیریت می‌شوند

        self._update_case_dependent_fields()

    def _on_case_type_changed(self, _checked: bool):
        """وقتی نوع پرونده عوض می‌شود، فیلدهای مبلغ مالیات/جریمه را به‌روزرسانی کن."""
        self._update_case_dependent_fields()

    def _update_case_dependent_fields(self):
        """نمایش/فعال‌سازی فیلدهای مبلغ مالیات و جریمه بر اساس نوع پرونده و داشتن برگه تشخیص."""
        has_ass = (self.group_has_ass.checkedId() == 1)

        # چه نوع پرونده‌هایی تیک خورده‌اند؟
        checked_case_labels = [
            lbl for lbl, cb in zip(self.case_types, self.case_checkboxes)
            if cb.isChecked()
        ]
        is_vat = "ارزش افزوده" in checked_case_labels
        is_perf = "مالیات بر عملکرد" in checked_case_labels

        # فقط ارزش افزوده؟ (هیچ نوع دیگری تیک نخورده)
        only_vat = is_vat and len(checked_case_labels) == 1

        # --- فیلد مبلغ مالیات اصلی ---
        # اگر فقط ارزش افزوده باشد → فیلد مبلغ مالیات غیرفعال و پاک شود
        if only_vat:
            self.penalty_amount.clear()
            self.penalty_amount.setEnabled(False)
        else:
            # در بقیه حالت‌ها، اگر برگه تشخیص دارد فعال می‌شود
            self.penalty_amount.setEnabled(has_ass)

        # --- فیلد جریمه مخصوص «مالیات بر عملکرد» ---
        if hasattr(self, "performance_penalty"):
            self.performance_penalty.setVisible(is_perf)
            self.performance_penalty.setEnabled(is_perf and has_ass)
            if not is_perf:
                self.performance_penalty.clear()

        # --- ردیف‌های دوره‌ای مخصوص ارزش افزوده ---
        if hasattr(self, "vat_period_rows"):
            for row_w, tax_edit, pen_edit in self.vat_period_rows:
                row_w.setVisible(is_vat)
                tax_edit.setEnabled(is_vat and has_ass)
                pen_edit.setEnabled(is_vat and has_ass)
                if not is_vat:
                    tax_edit.clear()
                    pen_edit.clear()

    def _update_assess_deadline(self):
        txt = self.assess_date.text().strip()
        if not validate_jalali(txt):
            self.assess_deadline.clear()
            return
        d = jdatetime.datetime.strptime(txt, "%Y/%m/%d")
        dd = d + jdatetime.timedelta(days=30)
        self.assess_deadline.setText(dd.strftime("%Y/%m/%d"))

    def _on_report_changed(self, id_):
        has_rep = (id_ == 1)
        if has_rep:
            # اگر گزارش رسیدگی دارد → تاریخ اعتراض و آپلود گزارش فعال
            self.appeal_send.setEnabled(True)
            self.report_upload_btn.setEnabled(True)
        else:
            # اگر گزارش رسیدگی ندارد → این‌ها همه خاموش و خالی
            self.appeal_send.clear()
            self.appeal_send.setEnabled(False)

            self.report_upload_btn.setEnabled(False)
            self.report_upload_list.clear()
            self.report_uploaded_files = []
    def _on_objected_changed(self, id_):
        is_obj = (id_ == 1)
        if is_obj:
            self.appeal_send.setEnabled(True)
            self.petition_upload_btn.setEnabled(True)
            self.mad238_entry_date.clear(); self.mad238_entry_date.setEnabled(False)
            self.mad238_agreement_deadline.clear(); self.mad238_agreement_deadline.setEnabled(False)
        else:
            self.appeal_send.clear(); self.appeal_send.setEnabled(False)
            self.petition_upload_btn.setEnabled(False)
            self.petition_upload_list.clear(); self.petition_uploaded_files = []
            self.mad238_entry_date.setEnabled(True)
            self._update_mad238_agreement_deadline()

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
    def _upload_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "انتخاب فایل‌ها", "", "فایل‌های مجاز (*.png *.jpg *.jpeg *.pdf *.txt *.docx *.doc *.xlsx)")
        if not files:
            QMessageBox.information(self, "", "هیچ فایلی انتخاب نشد")
            return
        # self.upload_list.clear()  # پاک نکن؛ افزایشی بهتره
        for src in files:
            name = os.path.basename(src)
            stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            dest = os.path.join(UPLOAD_ROOT, f"{os.path.splitext(name)[0]}_{stamp}{os.path.splitext(name)[1]}")
            shutil.copy2(src, dest)
            self.uploaded_files.append(dest)
            self._add_file_item(self.upload_list, dest, "upload")

    def _upload_petition_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "انتخاب فایل‌های لایحه", "", "فایل‌های مجاز (*.png *.jpg *.jpeg *.pdf *.txt *.docx *.doc *.xlsx)")
        if not files:
            QMessageBox.information(self, "", "هیچ فایلی انتخاب نشد")
            return
        for src in files:
            name = os.path.basename(src)
            stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            dest = os.path.join(UPLOAD_ROOT, f"{os.path.splitext(name)[0]}_{stamp}{os.path.splitext(name)[1]}")
            shutil.copy2(src, dest)
            self.petition_uploaded_files.append(dest)
            self._add_file_item(self.petition_upload_list, dest, "petition")
    def _upload_report_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "انتخاب فایل‌های گزارش رسیدگی",
            "",
            "همه فایل‌ها (*.*);;فایل‌های مجاز (*.png *.jpg *.jpeg *.pdf *.txt *.docx *.doc *.xlsx)"
        )
        if not files:
            QMessageBox.information(self, "", "هیچ فایلی انتخاب نشد")
            return

        for src in files:
            name = os.path.basename(src)
            stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            dest = os.path.join(
                UPLOAD_ROOT,
                f"{os.path.splitext(name)[0]}_{stamp}{os.path.splitext(name)[1]}"
            )
            shutil.copy2(src, dest)
            self.report_uploaded_files.append(dest)
            self._add_file_item(self.report_upload_list, dest, "report")
    def _on_refer_toggled(self, checked: bool):
        self.bodavi.setEnabled(checked)
        if checked:
            self.bodavi.start()
            self.tajdid.setEnabled(False); self.tajdid.reset(disable_all=True)
        else:
            self.bodavi.reset(disable_all=True)
            self.tajdid.reset(disable_all=True); self.tajdid.setEnabled(False)

    def _on_bodavi_obj_yes_toggled(self, checked: bool):
        if checked:
            if hasattr(self.tajdid, "reset"): self.tajdid.reset(disable_all=False)
            self.tajdid.setEnabled(True)
            if hasattr(self.tajdid, "start"): self.tajdid.start()
            if hasattr(self.tajdid, "refer_date"):
                self.tajdid.refer_date.setEnabled(True)
                self.tajdid.refer_date.setFocus()

    def _on_bodavi_obj_no_toggled(self, checked: bool):
        if checked:
            if hasattr(self.tajdid, "reset"): self.tajdid.reset(disable_all=True)
            self.tajdid.setEnabled(False)

    # ---------- Helpers ----------
    def _is_238_expired(self) -> bool:
        md = self.mad238_agreement_deadline.text().strip()
        if not validate_jalali(md):
            return False
        dd = jdatetime.datetime.strptime(md, "%Y/%m/%d").date()
        return dd <= jdatetime.date.today()

    def _lock_bodavi_tajdid(self, disable: bool):
        for rb in (self.rb_adjust, self.rb_refer):
            rb.setEnabled(not disable)
            if disable:
                rb.setAutoExclusive(False); rb.setChecked(False); rb.setAutoExclusive(True)

        if disable:
            if hasattr(self.bodavi, "reset"): self.bodavi.reset(disable_all=True)
            self.bodavi.setEnabled(False)
            if hasattr(self.tajdid, "reset"): self.tajdid.reset(disable_all=True)
            self.tajdid.setEnabled(False)

    # --- قرار دادن پنجره در مرکز مانیتور ---
    
    def showEvent(self, e):
        super().showEvent(e)
        try:
            fg = self.frameGeometry()
            center = self.screen().availableGeometry().center()
            fg.moveCenter(center)
            self.move(fg.topLeft())
        except Exception:
            pass

    # --- دکمه نوتیف: باز کردن دیالوگ ---
    def _open_notif_dialog(self):
        dlg = NotificationSettingsDialog(self)
        dlg.exec()

    # ---------- DB helpers (replacing Google Sheets) ----------
    def _save_to_db(self, rec: dict) -> bool:
        """Save record to database using tax_logic."""
        if not tax_logic:
            return False
        try:
            result = tax_logic.save_company(rec)
            return result is not None
        except Exception as e:
            print(f"DB save failed: {e}")
            return False

    def _is_duplicate_local(self, company_name: str, fiscal_year: str, case_type: str) -> bool:
        """Check if company/fiscal year/case type already exists in DB."""
        if not tax_logic:
            return False
        try:
            companies = tax_logic.load_companies()
            for comp in companies:
                if (comp.get('company_name', '').strip() == company_name.strip() and
                    str(comp.get('fiscal_year', '')).strip() == str(fiscal_year).strip() and
                    comp.get('case_type', '').strip() == case_type.strip()):
                    return True
        except Exception:
            pass
        return False

    def _save_local_copy(self, rec: dict):
        """Legacy function - now uses DB instead of JSON files."""
        # This is called by _finalize, which now uses DB
        pass

    # ---------- ذخیره (منطق کامل تو – بدون تغییر) ----------
    def _save(self):
        # --- اعتبارسنجی‌های پایه ---
        nid = self.national_id.text().strip()
        if not (nid and nid.isdigit()):
            QMessageBox.warning(self, "اجباری", "شناسه ملی الزامی است")
            return
        archive = self.archive.text().strip()
        if not archive:
            QMessageBox.warning(self, "اجباری", "شماره بایگانی الزامی است")
            return
        if not self.company.text().strip():
            QMessageBox.warning(self, "اجباری", "نام شرکت الزامی است")
            return

        fy = self.fiscal.text().strip()
        if not (fy.isdigit() and len(fy) == 4):
            QMessageBox.warning(self, "اجباری", "سال مالی باید ۴ رقم باشد")
            return

# تاریخ ورود اختیاری است: اگر خالی بود (حتی با ماسک ___/__/__) خطا نده
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
            QMessageBox.warning(self, "اجباری", "حداقل یک نوع پرونده را انتخاب کنید")
            return
        selected_cases_str = "، ".join(selected_cases)

        # جلوگیری از تکراری (لوکال)
        if self._is_duplicate_local(self.company.text().strip(), fy, selected_cases_str):
            QMessageBox.critical(self, "تکراری", "این ترکیب نام شرکت/سال مالی/نوع پرونده قبلاً ثبت شده است.")
            return

        sub = self.submit_date.text().strip()
        if not validate_jalali(sub):
            QMessageBox.warning(self, "اجباری", "تاریخ ارائه اسناد و مدارک را وارد کنید")
            return

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
        rec_id = str(uuid.uuid4())

        # ✅ مسیر سریع اگر مهلت ارائه نگذشته
        if due_j and due_j > today_j:
            rec_quick = {
                'id': rec_id,
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
                'report_uploaded_files': self.report_uploaded_files,
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

        # تشخیص اینکه فقط «ارزش افزوده» تیک خورده یا نه
        selected_cases_now = [cb.text() for cb in getattr(self, 'case_checkboxes', []) if cb.isChecked()]
        only_vat = ("ارزش افزوده" in selected_cases_now) and (len(selected_cases_now) == 1)

        amt_txt = self.penalty_amount.text().replace(",", "").strip()
        # اگر فقط ارزش افزوده باشد، این فیلد اجباری نیست
        if has_ass and not amt_txt and not only_vat:
            QMessageBox.warning(self, "اجباری", "مبلغ مالیات را وارد کنید")
            return
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
            'id': rec_id,
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
            'appeal_send_date': pet ,
            'petition_uploaded_files': self.petition_uploaded_files,
            'mad238_entry_date': self.mad238_entry_date.text().strip(),
            'mad238_agreement_deadline': self.mad238_agreement_deadline.text().strip(),
            'jarime_amount': int(amt_txt) if (has_ass and amt_txt) else "",
            'notes': self.notes_w.get_notes(),
            'notify_days': self.global_settings.get('notify_days', ""),
            'notify_mode': self.global_settings.get('notify_mode', "")
        }

        # مقادیر تکمیلی مخصوص نوع پرونده‌ها (عملکرد / ارزش افزوده)
        perf_pen_txt = ""
        if hasattr(self, "performance_penalty"):
            perf_pen_txt = self.performance_penalty.text().replace(",", "").strip()
        rec_base['performance_penalty'] = int(perf_pen_txt) if perf_pen_txt else ""

        if hasattr(self, "vat_period_rows"):
            for idx_p, (_row_w, tax_edit, pen_edit) in enumerate(self.vat_period_rows, start=1):
                tax_txt = tax_edit.text().replace(",", "").strip()
                pen_txt = pen_edit.text().replace(",", "").strip()
                rec_base[f'vat_p{idx_p}_tax'] = int(tax_txt) if tax_txt else ""
                rec_base[f'vat_p{idx_p}_penalty'] = int(pen_txt) if pen_txt else ""

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
                        try:
                            self._merge_tajdid_into_rec(rec_base, t_data or {})
                        except Exception:
                            pass
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

                    # 4) اگر احراز دبیرخانه شورا = بله → اگر تاریخ شورا خالی/گذشته بود، فرم یادآوری باز شود؛ اگر امروز/آینده بود، همان تاریخ ثبت شود
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
# --- End of new overrides (v2) ---
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

        # مهلت اعتراض برگه تشخیص
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

        # شاخه اختصاصی وضعیت = ارائه شد
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

        # یادآوری کلی
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


    # ---------- نهایی‌سازی و بازسازی فرم ----------
    def _finalize(self, rec: dict):
        """ثبت نهایی رکورد در دیتابیس، نمایش پیام موفقیت، و بازسازی فرم."""
        # Save to database (replaces JSON file + Google Sheets)
        if not self._save_to_db(rec):
            QMessageBox.warning(self, "هشدار", "ذخیره در دیتابیس موفق نبود. ممکن است دیتابیس آماده نباشد.")
            # Still proceed with form reload

        # پیام موفقیت
        try:
            QMessageBox.information(self, "ثبت", "رکورد با موفقیت ثبت شد")
        except Exception:
            pass

        # بازسازی کامل فرم
        try:
            self.reload_form()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"بازسازی فرم ناموفق بود:\n{e}")
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())