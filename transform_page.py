# -*- coding: utf-8 -*-
# transform_page.py — فرم وسط‌چین به سبک «عباسپور» + مقدار ثابت فقط برای ستون‌های مشخص (با تشخیص منعطف)
"""
UI تبدیل به الگوی ثابت با چیدمان وسط‌چین شبیه abbaspoor_page:
- قاب مرکزی وسط‌چین با عرض محدود
- Styled* و FormCard از abbaspoor_page در صورت وجود؛ وگرنه فال‌بک
- QSS از styles/abbaspoor.qss اگر موجود باشد
- «فیلد مقدار ثابت (اختیاری)» فقط برای این‌ها ساخته می‌شود:
    تلفن همراه، کد پستی، مبلغ تخفیف، سایر اضافات، مبلغ مالیات و عوارض
  (تشخیص با تطابق دقیق + الگوهای منعطف و معادل‌های رایج فارسی/لاتین)
"""

from __future__ import annotations

import os
import re
import sys
import importlib.util
import pandas as pd
from PySide6 import QtWidgets, QtGui, QtCore

from transform_logic import (
    TEMPLATE_COLUMNS, FIXED_BLANK_COLUMNS,
    suggest_mapping, build_output, write_output_excel
)

# --- فیلتر برای جلوگیری از تغییر کمبوباکس با اسکرول ماوس ---
class _BlockWheel(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Wheel:
            # اجازه نده آیتم‌های کمبو با اسکرول عوض شوند،
            # ولی رویداد را به والد بفرست تا اسکرول‌اِریا حرکت کند
            QtWidgets.QApplication.sendEvent(obj.parent(), event)
            return True
        return super().eventFilter(obj, event)

from ui.widgets import StyledLineEdit, StyledComboBox, StyledButton  # type: ignore
try:
    from ui.widgets import FormCard  # type: ignore
except Exception:
    FormCard = QtWidgets.QFrame

# --- تنظیمات/ابزار ---
DPI = 96
def inch(x: float) -> int: return int(x * DPI)

def _disable_first_item(combo: QtWidgets.QComboBox):
    """اولین آیتم کمبو را (placeholder) غیرفعال می‌کند؛ سازگار با QStandardItemModel."""
    model = combo.model()
    if isinstance(model, QtGui.QStandardItemModel):
        it = model.item(0)
        if it:
            it.setEnabled(False)

def _try_load_qss(widget: QtWidgets.QWidget) -> None:
    """لود استایل «styles/abbaspoor.qss» اگر موجود باشد."""
    candidates = [
        os.path.join(os.path.dirname(__file__), 'styles', 'abbaspoor.qss'),
        os.path.join(os.getcwd(), 'styles', 'abbaspoor.qss'),
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    widget.setStyleSheet(f.read())
                break
            except Exception:
                pass

# --- تشخیص منعطف اینکه آیا ستون مقصد باید «مقدار ثابت» داشته باشد یا نه ---
_ALLOWED_CONST_EXACT = {
    "تلفن همراه",
    "کد پستی",
    "مبلغ تخفیف",
    "سایر اضافات",
    "مبلغ مالیات و عوارض",
}
def _clean(s: str) -> str:
    if not s:
        return ""
    s = str(s)
    s = s.replace("ي", "ی").replace("ك", "ک").replace("\u200c", "")  # ی/ک و ZWNJ
    s = s.lower()
    s = re.sub(r"[\s\-_]+", "", s)  # حذف فاصله/خط تیره/زیرخط
    return s

_ALLOWED_CONST_EXACT_NORM = {_clean(n) for n in _ALLOWED_CONST_EXACT}

# الگوهای انعطاف‌پذیر (فارسی/لاتین)
# دقت: الگوها طوری‌اند که «مبلغ مالیات/عوارض» رو بگیرند ولی «درصد مالیات» رو نگیرند.
_PATTERNS = [
    # تلفن همراه / موبایل / mobile / cell phone
    re.compile(r"(تلفن.*همراه|موبایل|موبايل|mobile|cell\s*phone|phone\s*number)", re.I),
    # کد پستی / postal code / zip code
    re.compile(r"(کد\s*پستی|کدپستی|postal\s*code|zip\s*code)", re.I),
    # مبلغ + تخفیف / discount amount
    re.compile(r"(مبلغ).*?(تخفیف)|(^|\b)discount(\s*amount)?($|\b)", re.I),
    # سایر + اضافات/هزینه‌ها / other/additional charges
    re.compile(r"(سایر).*(اضافات|هزینه|هزینه‌ها|هزينهها)|other\s*(charges|fees)|additional\s*(charges|fees)", re.I),
    # مبلغ + (مالیات|عوارض) / tax amount / duty amount / VAT amount
    re.compile(r"(مبلغ).*(مالیات|عوارض)|tax\s*amount|duty\s*amount|vat\s*amount", re.I),
]

def needs_const_field(target_col: str) -> bool:
    # تطابق دقیق (نرمال‌شده)
    if _clean(target_col) in _ALLOWED_CONST_EXACT_NORM:
        return True
    # تطابق با الگوهای انعطاف‌پذیر
    t = str(target_col or "")
    for pat in _PATTERNS:
        if pat.search(t):
            # برای مالیات: اگر «درصد» آمده باشد و «مبلغ» نیامده باشد، رد کن
            if "مالیات" in t or "عوارض" in t or re.search(r"(tax|vat|duty)", t, re.I):
                if ("درصد" in t or re.search(r"percent|rate", t, re.I)) and ("مبلغ" not in t and not re.search(r"amount", t, re.I)):
                    continue
            return True
    return False


# --- ویجت ردیف نگاشت ---
class MappingRow(QtWidgets.QWidget):
    """
    یک ردیف نگاشت برای یک ستون مقصد:
    - لیبل نام ستون مقصد
    - Combo انتخاب ستون مبدا (از شیت ورودی) با placeholder غیرفعال
    - LineEdit مقدار ثابت (اختیاری) فقط اگر needs_const_field(...) True باشد
    """
    def __init__(self, target_col: str, parent=None):
        super().__init__(parent)
        self.target_col = target_col
        self._has_const = needs_const_field(target_col)

        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.lbl = QtWidgets.QLabel(target_col)
        self.lbl.setMinimumWidth(220)

        self.combo = StyledComboBox()
        # بلاک اسکرول روی کمبو
        self._wheelBlocker = _BlockWheel(self)
        self.combo.installEventFilter(self._wheelBlocker)
        # placeholder غیرفعال: با ستاپ اولیه تا قبل از بارگذاری ستون‌ها
        self.combo.addItem("انتخاب ستون")
        _disable_first_item(self.combo)

        lay.addWidget(self.lbl, 0, QtCore.Qt.AlignRight)
        lay.addWidget(self.combo, 1)

        self.const_edit = None
        if self._has_const:
            self.const_edit = StyledLineEdit("مقدار ثابت (اختیاری)")
            lay.addWidget(self.const_edit, 1)
        else:
            lay.addStretch(1)

    def set_sources(self, cols: list[str]):
        current = self.combo.currentText()
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItem("انتخاب ستون")
        _disable_first_item(self.combo)
        self.combo.addItems(list(map(str, cols)))
        # بازگردانی انتخاب قبلی اگر موجود بود
        if current and current != "انتخاب ستون":
            idx = self.combo.findText(current, QtCore.Qt.MatchFixedString)
            self.combo.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            self.combo.setCurrentIndex(0)
        self.combo.blockSignals(False)

    def apply_mapping(self, piece: dict):
        self.apply_mapping_piece(piece)  # برای سازگاری به عقب

    def apply_mapping_piece(self, piece: dict):
        src = (piece or {}).get('source') or ""
        const = (piece or {}).get('const') or ""
        if self.const_edit is not None:
            self.const_edit.setText(const)
        if src:
            idx = self.combo.findText(src, QtCore.Qt.MatchFixedString)
            if idx >= 0:
                self.combo.setCurrentIndex(idx)

    def set_suggestion(self, src_name: str | None):
        if not src_name:
            return
        idx = self.combo.findText(src_name, QtCore.Qt.MatchFixedString)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)

    def value(self) -> dict:
        src_text = self.combo.currentText().strip()
        if self.combo.currentIndex() <= 0:
            src_text = ""
        return {
            'source': src_text,
            'const': (self.const_edit.text() if self.const_edit is not None else "")
        }


# --- صفحهٔ اصلی تبدیل ---
class TransformPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TransformPage")
        self.setWindowTitle("تبدیل به الگوی ثابت - عباسپور")
        self.setLayoutDirection(QtCore.Qt.RightToLeft)

        self.src_cols: list[str] = []  # ستون‌های شیت ورودی برای تغذیه‌ی کمبوها

        # لایهٔ اصلی: وسط‌چین مثل abbaspoor_page
        layout_main = QtWidgets.QHBoxLayout(self)
        layout_main.setContentsMargins(0, 0, 0, 0)
        layout_main.setAlignment(QtCore.Qt.AlignCenter)

        # قاب مرکزی محدودعرض
        frame = FormCard()
        frame.setObjectName("AbbaspoorFrame")
        frame.setMaximumWidth(inch(10.64))
        frame.setMaximumHeight(inch(8))
        layout_main.addWidget(frame)

        v = QtWidgets.QVBoxLayout(frame)
        v.setContentsMargins(30, 30, 30, 30)
        v.setSpacing(16)

        # === ورودی فایل ===
        h_in = QtWidgets.QHBoxLayout(); h_in.setSpacing(10)
        self.file_in = StyledLineEdit("فایل ورودی (xlsx)")
        btn_browse_in = StyledButton("انتخاب…")
        btn_browse_in.clicked.connect(self._pick_in)
        h_in.addWidget(self.file_in, 1); h_in.addWidget(btn_browse_in)
        v.addLayout(h_in)

        # === انتخاب شیت (ردیف مستقل) ===
        row_sheets = QtWidgets.QGridLayout()
        row_sheets.setHorizontalSpacing(10); row_sheets.setVerticalSpacing(6)

        lbl_sheet = QtWidgets.QLabel("شیت ورودی:")
        self.combo_sheet = StyledComboBox()
        # بلاک اسکرول روی کمبو
        self._sheetWheelBlocker = _BlockWheel(self)
        self.combo_sheet.installEventFilter(self._sheetWheelBlocker)
        # placeholder غیرفعال مثل abbaspoor_page
        self.combo_sheet.addItem("انتخاب شیت")
        _disable_first_item(self.combo_sheet)

        row_sheets.addWidget(lbl_sheet,        0, 0, alignment=QtCore.Qt.AlignRight)
        row_sheets.addWidget(self.combo_sheet, 0, 1)
        row_sheets.setColumnStretch(0, 0); row_sheets.setColumnStretch(1, 1)
        v.addLayout(row_sheets)

        # وقتی کاربر واقعاً یک شیت انتخاب کرد، آنگاه ستون‌ها را بارگذاری کن
        self.combo_sheet.currentIndexChanged.connect(self._on_sheet_changed)

        # === نگاشت ستون‌ها ===
        map_box = QtWidgets.QGroupBox("معادل سازی")
        map_lay = QtWidgets.QVBoxLayout(map_box)
        map_lay.setContentsMargins(10, 20, 10, 10)
        map_lay.setSpacing(6)

        # نوار ابزار پیشنهاد/پاک‌سازی حذف شد به درخواست کاربر

        self.rows_container = QtWidgets.QWidget()
        self.rows_layout = QtWidgets.QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(6)

        self.rows: dict[str, MappingRow] = {}
        for tcol in TEMPLATE_COLUMNS:
            r = MappingRow(tcol, self.rows_container)
            self.rows_layout.addWidget(r)
            self.rows[tcol] = r
        self.rows_layout.addStretch(1)

        # اسکرول‌دار کردن بخش نگاشت برای جلوگیری از بزرگ‌شدن پنجره
        self.rows_scroll = QtWidgets.QScrollArea()
        self.rows_scroll.setWidgetResizable(True)
        self.rows_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.rows_scroll.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.rows_scroll.setWidget(self.rows_container)

        map_lay.addWidget(self.rows_scroll)
        v.addWidget(map_box)

        # === خروجی ===
        h_out = QtWidgets.QHBoxLayout(); h_out.setSpacing(10)
        self.file_out = StyledLineEdit("مسیر ذخیره خروجی (xlsx)")
        btn_browse_out = StyledButton("ذخیره در…")
        btn_browse_out.clicked.connect(self._pick_out)
        h_out.addWidget(self.file_out, 1); h_out.addWidget(btn_browse_out)
        v.addLayout(h_out)

        # === دکمه اجرا ===
        btn_run = StyledButton("ساخت فایل خروجی")
        btn_run.setFixedWidth(220)
        btn_run.clicked.connect(self._run)
        v.addWidget(btn_run, 0, QtCore.Qt.AlignCenter)

        v.addStretch(1)

        # حداقل سایز منطقی تا لایه‌ها پنجره را به اندازهٔ مانیتور نکِشند
        self.setMinimumSize(900, 600)

        # QSS بعد از ساخت ویجت‌ها
        _try_load_qss(self)

        # دکمه‌های پیشنهاد/پاکسازی حذف شده‌اند

    # ---------- Helpers ----------
    def _warn(self, title: str, msg: str):
        QtWidgets.QMessageBox.warning(self, title, msg)

    def _on_sheet_changed(self, idx: int):
        if idx <= 0:
            return
        sheet_name = self.combo_sheet.itemText(idx)
        self._load_src_cols(sheet_name)

    def _pick_in(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "انتخاب فایل ورودی", "", "Excel (*.xlsx)")
        if not path:
            return
        self.file_in.setText(path)
        try:
            sheets = pd.ExcelFile(path).sheet_names
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", str(e)); return

        # placeholder غیرفعال + لیست شیت‌ها
        self.combo_sheet.blockSignals(True)
        self.combo_sheet.clear()
        self.combo_sheet.addItem("انتخاب شیت")
        _disable_first_item(self.combo_sheet)
        self.combo_sheet.addItems(sheets)
        self.combo_sheet.setCurrentIndex(0)  # تا کاربر صریحاً انتخاب کند
        self.combo_sheet.blockSignals(False)

        # تا قبل از انتخاب شیت، ستون‌ها ریست شوند
        self.src_cols = []
        for r in self.rows.values():
            r.set_sources([])

    def _pick_out(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "مسیر ذخیره خروجی", "", "Excel (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        self.file_out.setText(path)

    def _load_src_cols(self, sheet_name: str):
        if not self.file_in.text() or not sheet_name:
            return
        try:
            df = pd.read_excel(self.file_in.text(), sheet_name=sheet_name, nrows=0)
            cols = list(map(str, df.columns))
        except Exception as e:
            self._warn("خطا در خواندن شیت", str(e)); return

        self.src_cols = cols
        for r in self.rows.values():
            r.set_sources(cols)


            # به‌محض انتخاب شیت، نگاشت‌های پیشنهادی روی کمبوها اعمال شود
            suggestions = suggest_mapping(self.src_cols)
            for tcol, r in self.rows.items():
                r.set_suggestion(suggestions.get(tcol))

            # قواعد اختصاصی کاربر: نگاشت‌های پیش‌فرض خاص
            # ۱) «سایر اضافات (ریال)» <- «مبلغ مالیات»
            # ۲) «مبلغ مالیات و عوارض (ریال)» <- «سایر عوارض»
            src_set = set(self.src_cols)
            overrides = {
                'سایر اضافات (ریال)': 'مبلغ مالیات',
                'مبلغ مالیات و عوارض (ریال)': 'سایر عوارض',
            }
            for tcol, src_name in overrides.items():
                if (tcol in self.rows) and (src_name in src_set):
                    self.rows[tcol].set_suggestion(src_name)

    def _collect_mapping(self) -> dict:
        return {tcol: r.value() for tcol, r in self.rows.items()}

    def _apply_mapping(self, mapping: dict):
        for tcol, piece in (mapping or {}).items():
            row = self.rows.get(tcol)
            if row:
                row.apply_mapping_piece(piece)

    # ---------- Actions ----------
    def _suggest(self):
        if not self.src_cols:
            self._warn("هشدار", "اول فایل و شیت ورودی را انتخاب کنید تا ستون‌ها بارگذاری شوند.")
        else:
            suggestions = suggest_mapping(self.src_cols)  # dict: target_col -> source_name
            for tcol, r in self.rows.items():
                r.set_suggestion(suggestions.get(tcol))

    def _clear_maps(self):
        for r in self.rows.values():
            r.combo.setCurrentIndex(0)
        for r in self.rows.values():
            if r.const_edit is not None:
                r.const_edit.clear()

    def _run(self):
        try:
            if not self.file_in.text().strip():
                raise ValueError("فایل ورودی انتخاب نشده است.")
            if not self.file_out.text().strip():
                raise ValueError("مسیر فایل خروجی مشخص نشده است.")
            if self.combo_sheet.currentIndex() <= 0:
                raise ValueError("شیت ورودی انتخاب نشده است.")

            sheet_name = self.combo_sheet.currentText().strip()

            # خواندن منبع
            df_src = pd.read_excel(self.file_in.text(), sheet_name=sheet_name)

            # نگاشت
            mapping = self._collect_mapping()

            # ساخت خروجی
            df_out = build_output(df_src, mapping, compute_tax_if_missing=True)

            # ستون‌های ثابتِ خالی (در صورت نیاز)
            for col in FIXED_BLANK_COLUMNS:
                if col not in df_out.columns:
                    df_out[col] = ""

            # نوشتن
            out_path = self.file_out.text()
            write_output_excel(df_out, out_path)
            QtWidgets.QMessageBox.information(self, "تمام", "فایل خروجی ساخته شد.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", str(e))


# --- راه‌اندازی ---
def main():
    app = QtWidgets.QApplication([])
    app.setApplicationName("تبدیل به الگوی ثابت - عباسپور")

    w = TransformPage()

    # اندازهٔ اولیه بر اساس فضای کار مانیتور (جلوگیری از QWindowsWindow::setGeometry warning)
    avail = QtGui.QGuiApplication.primaryScreen().availableGeometry()
    w.resize(min(1100, max(900, avail.width() - 80)),
             min(740,  max(600, avail.height() - 80)))
    # مرکز صفحه
    geo = w.frameGeometry()
    geo.moveCenter(avail.center())
    w.move(geo.topLeft())

    w.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())