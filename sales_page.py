# -*- coding: utf-8 -*-
# sales_page.py — فرم وسط‌چین جمع‌وجور + یک‌ردیفه‌کردن شیت‌ها
"""
رابط کاربری PySide6 با چیدمان شبیه abbaspoor_page:
- قاب مرکزی وسط‌چین با عرض محدود
- ردیف اول: «شیت موجودی: [Combo]» و «شیت مشتریان: [Combo]» کنار هم و فقط همین‌ها
- ارتفاع کلی کمتر (spacing/margins/controls کوتاه‌تر)
- فیلدهای «عوارض ۶۰٪» و «عوارض ۴۰٪» فقط placeholder دارند (بدون مقدار پیش‌فرض)
- منطق برنامه (sales_logic) دست‌نخورده
"""

import os
import re
import pandas as pd
from PySide6 import QtWidgets, QtGui, QtCore


from sales_logic import load_next_defaults ,PERSIAN_DIGITS, generate_sales, write_output_excel


# تلاش برای استفاده از ویجت‌های استایل عباسپور
try:
    from ui.widgets import StyledLineEdit, StyledComboBox, StyledButton
    _HAS_ABBASPOOR_STYLED = True
except Exception:
    _HAS_ABBASPOOR_STYLED = False

    class StyledLineEdit(QtWidgets.QLineEdit):
        def __init__(self, placeholder: str = "", parent=None):
            super().__init__(parent)
            if placeholder:
                self.setPlaceholderText(placeholder)
            self.setFixedHeight(34)  # کوتاه‌تر

    class StyledComboBox(QtWidgets.QComboBox):
        def __init__(self, placeholder: str = "", parent=None):
            super().__init__(parent)
            self.setEditable(False)
            self.setFixedHeight(34)  # کوتاه‌تر

    class StyledButton(QtWidgets.QPushButton):
        def __init__(self, text: str = "", parent=None):
            super().__init__(text, parent)
            self.setFixedHeight(34)  # کوتاه‌تر

# --- تنظیمات ---
DPI = 96
def inch(x: float) -> int: return int(x * DPI)

JDATE_RX = QtCore.QRegularExpression(r'^\d{4}/\d{2}/\d{2}$')

def _try_load_qss(widget: QtWidgets.QWidget) -> None:
    """لود استایل در صورت وجود."""
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


class SalesPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SalesPage")
        self.setLayoutDirection(QtCore.Qt.RightToLeft)

        # استایل
        _try_load_qss(self)

        # لایهٔ اصلی: وسط‌چین
        layout_main = QtWidgets.QHBoxLayout(self)
        layout_main.setContentsMargins(0, 0, 0, 0)
        layout_main.setAlignment(QtCore.Qt.AlignCenter)

        # قاب مرکزی با عرض محدود
        frame = QtWidgets.QFrame()
        frame.setObjectName("AbbaspoorFrame")
        frame.setMaximumWidth(inch(10.64))
        frame.setMaximumHeight(inch(9.2))
        layout_main.addWidget(frame)

        # بدنهٔ قاب مرکزی – جمع‌وجورتر
        v = QtWidgets.QVBoxLayout(frame)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(12)

        # ===== 1) فایل ورودی =====
        h_in = QtWidgets.QHBoxLayout(); h_in.setSpacing(10)
        self.file_in = StyledLineEdit("فایل ورودی (xlsx)")
        btn_browse_in = StyledButton("انتخاب…")
        btn_browse_in.clicked.connect(self._pick_in)
        h_in.addWidget(self.file_in, 1); h_in.addWidget(btn_browse_in)
        v.addLayout(h_in)

        # ===== 2) ردیف شیت‌ها (فقط همین دو تا در این ردیف) =====
        grid_top = QtWidgets.QGridLayout()
        grid_top.setHorizontalSpacing(10); grid_top.setVerticalSpacing(8)

        lbl_inv = QtWidgets.QLabel("شیت موجودی:")
        self.sheet_inv = StyledComboBox("انتخاب شیت موجودی")

        lbl_cust = QtWidgets.QLabel("شیت مشتریان:")
        self.sheet_cust = StyledComboBox("انتخاب شیت مشتریان")

        # ردیف 0: فقط لیبل و کمبوهای موجودی و مشتری
        grid_top.addWidget(lbl_inv,   0, 0, alignment=QtCore.Qt.AlignRight)
        grid_top.addWidget(self.sheet_inv, 0, 1)
        grid_top.addWidget(lbl_cust,  0, 2, alignment=QtCore.Qt.AlignRight)
        grid_top.addWidget(self.sheet_cust, 0, 3)

        # ===== 3) پارامترهای کلیدی =====
        # ردیف 1: شماره شروع فاکتور + شناسه سند شروع (بدون لیبل، placeholder داخل فیلد)
        self.inv_no = StyledLineEdit("شماره شروع فاکتور")
        self.doc_id = StyledLineEdit("شناسه سند شروع")
        # پر کردن پیش‌فرض‌ها بر اساس state
        try:
            _n_inv, _n_doc = load_next_defaults(default_invoice=None)
            if _n_inv is not None:
                self.inv_no.setText(str(_n_inv))
            self.doc_id.setText(str(_n_doc))
        except Exception:
            pass
        grid_top.addWidget(self.inv_no, 1, 1)
        grid_top.addWidget(self.doc_id, 1, 3)

        # ردیف 2: حداقل مبلغ + حداکثر مبلغ
        self.min_amt = StyledLineEdit("حداقل مبلغ")
        self.max_amt = StyledLineEdit("حداکثر مبلغ")
        grid_top.addWidget(self.min_amt, 2, 1)
        grid_top.addWidget(self.max_amt, 2, 3)

        # ردیف 3: تاریخ‌ها (placeholder داخل فیلدها)
        self.date_from = StyledLineEdit("از تاریخ (YYYY/MM/DD)")
        self.date_to   = StyledLineEdit("تا تاریخ (YYYY/MM/DD)")
        rx = QtGui.QRegularExpressionValidator(JDATE_RX, self)
        self.date_from.setValidator(rx)
        self.date_to.setValidator(rx)
        grid_top.addWidget(self.date_from, 3, 1)
        grid_top.addWidget(self.date_to,   3, 3)

        # ردیف 4 و 5: عوارض‌ها (بدون مقدار پیش‌فرض، فقط placeholder)
        self.duty60 = StyledLineEdit("عوارض مالیات ۶۰٪")
        self.duty40 = StyledLineEdit("عوارض مالیات ۴۵٪")
        grid_top.addWidget(self.duty60, 4, 1)
        grid_top.addWidget(self.duty40, 4, 3)
        # ردیف 5: درصد عوارض آسیب‌رسان
        self.harmful_pct = StyledLineEdit("درصد عوارض آسیب‌رسان")
        grid_top.addWidget(self.harmful_pct, 5, 1)

        grid_top.setColumnStretch(0, 0)
        grid_top.setColumnStretch(1, 1)
        grid_top.setColumnStretch(2, 0)
        grid_top.setColumnStretch(3, 1)
        v.addLayout(grid_top)

        # اتصال برای بارگذاری ستون‌ها
        self.sheet_inv.currentTextChanged.connect(self._load_inv_cols)
        self.sheet_cust.currentTextChanged.connect(self._load_cust_cols)

        # ===== 4) گروه ستون‌ها (معادل‌سازی) =====
        hb_maps = QtWidgets.QHBoxLayout(); hb_maps.setSpacing(10)

        inv_box = QtWidgets.QGroupBox("ستون‌های موجودی")
        inv_form = QtWidgets.QFormLayout(inv_box)
        inv_form.setLabelAlignment(QtCore.Qt.AlignRight)
        inv_form.setHorizontalSpacing(10); inv_form.setVerticalSpacing(6)

        self.inv_map = {}
        def _mk_inv(label, key):
            cb = StyledComboBox(); cb.addItem("")  # allow empty first
            self.inv_map[key] = cb; inv_form.addRow(QtWidgets.QLabel(label + ":"), cb)

        _mk_inv("کد کالا",     "code")
        _mk_inv("شناسه کالا",  "id")
        _mk_inv("نام کالا",    "name")
        _mk_inv("قیمت فروش",   "price")
        _mk_inv("موجودی",      "quantity")
        _mk_inv("فی خرید",     "buy_price")
        _mk_inv("مالیات",      "tax_pct")

        cust_box = QtWidgets.QGroupBox("ستون‌های مشتری")
        cust_form = QtWidgets.QFormLayout(cust_box)
        cust_form.setLabelAlignment(QtCore.Qt.AlignRight)
        cust_form.setHorizontalSpacing(10); cust_form.setVerticalSpacing(6)

        self.cust_map = {}
        def _mk_cust(label, key):
            cb = StyledComboBox(); cb.addItem("")
            self.cust_map[key] = cb; cust_form.addRow(QtWidgets.QLabel(label + ":"), cb)

        _mk_cust("کد مشتری", "code")
        _mk_cust("نام مشتری", "name")

        hb_maps.addWidget(inv_box, 1); hb_maps.addWidget(cust_box, 1)
        v.addLayout(hb_maps)

        # ===== 5) فایل خروجی =====
        h_out = QtWidgets.QHBoxLayout(); h_out.setSpacing(10)
        self.file_out = StyledLineEdit("مسیر ذخیره خروجی (xlsx)")
        btn_browse_out = StyledButton("ذخیره در…")
        btn_browse_out.clicked.connect(self._pick_out)
        h_out.addWidget(self.file_out, 1); h_out.addWidget(btn_browse_out)
        v.addLayout(h_out)

        # ===== 6) دکمه اجرا =====
        btn_run = StyledButton("ایجاد و ذخیره خروجی")
        btn_run.setFixedWidth(200)
        btn_run.clicked.connect(self._run)
        v.addWidget(btn_run, 0, QtCore.Qt.AlignCenter)

        v.addStretch()

    # ---------- Helpers ----------
    def _warn(self, title, msg):
        QtWidgets.QMessageBox.warning(self, title, msg)

    def _pick_in(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "انتخاب فایل ورودی", "", "Excel (*.xlsx)")
        if not path:
            return
        self.file_in.setText(path)
        try:
            sheets = pd.ExcelFile(path).sheet_names
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", str(e)); return
        self.sheet_inv.clear();  self.sheet_inv.addItems(sheets)
        self.sheet_cust.clear(); self.sheet_cust.addItems(sheets)
        if sheets:
            self.sheet_inv.setCurrentIndex(0)
            self.sheet_cust.setCurrentIndex(0)
            self._load_inv_cols(self.sheet_inv.currentText())
            self._load_cust_cols(self.sheet_cust.currentText())

    def _pick_out(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "مسیر ذخیره خروجی", "", "Excel (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        self.file_out.setText(path)

    def _load_inv_cols(self, sheet_name: str):
        self._load_cols(sheet_name, self.inv_map)

    def _load_cust_cols(self, sheet_name: str):
        self._load_cols(sheet_name, self.cust_map)

    def _load_cols(self, sheet_name: str, mapping: dict):
        if not self.file_in.text() or not sheet_name:
            return
        try:
            df = pd.read_excel(self.file_in.text(), sheet_name=sheet_name, nrows=0)
            cols = list(map(str, df.columns))
        except Exception as e:
            self._warn("خطا در خواندن شیت", str(e)); return
        for cb in mapping.values():
            cb.clear(); cb.addItems([""] + cols)
            cb.setCurrentIndex(0)

    # ---------- Run ----------
    def _run(self):
        try:
            # مسیرها
            if not self.file_in.text().strip():
                raise ValueError("فایل ورودی انتخاب نشده است.")
            if not self.file_out.text().strip():
                raise ValueError("مسیر فایل خروجی مشخص نشده است.")

            # خواندن داده‌ها
            inv  = pd.read_excel(self.file_in.text(), sheet_name=self.sheet_inv.currentText())
            cust = pd.read_excel(self.file_in.text(), sheet_name=self.sheet_cust.currentText())

            # مپ ستون‌ها
            inv_cols  = {k: cb.currentText().strip() for k, cb in self.inv_map.items()}
            cust_cols = {k: cb.currentText().strip() for k, cb in self.cust_map.items()}

            for req in ['code', 'id', 'name', 'price', 'quantity', 'buy_price', 'tax_pct']:
                if not inv_cols.get(req):
                    raise ValueError(f"ستون «{req}» در معادل‌سازی موجودی انتخاب نشده است.")
            for req in ['code', 'name']:
                if not cust_cols.get(req):
                    raise ValueError(f"ستون «{req}» در معادل‌سازی مشتریان انتخاب نشده است.")

            # تاریخ‌ها
            date_from = self.date_from.text().translate(PERSIAN_DIGITS)
            date_to   = self.date_to.text().translate(PERSIAN_DIGITS)
            if not (re.fullmatch(r'\d{4}/\d{2}/\d{2}', date_from) and re.fullmatch(r'\d{4}/\d{2}/\d{2}', date_to)):
                raise ValueError("فرمت تاریخ‌ها باید YYYY/MM/DD باشد.")

            # پارامترها
            required = [self.inv_no, self.doc_id, self.min_amt, self.max_amt]
            if any(not w.text().strip() for w in required):
                raise ValueError("فیلدهای «شماره شروع فاکتور»، «شناسه سند شروع»، «حداقل مبلغ»، «حداکثر مبلغ» نباید خالی باشند.")

            inv_no  = int(self.inv_no.text().translate(PERSIAN_DIGITS))
            doc_id  = int(self.doc_id.text().translate(PERSIAN_DIGITS))
            min_amt = int(self.min_amt.text().replace(',', '').translate(PERSIAN_DIGITS))
            max_amt = int(self.max_amt.text().replace(',', '').translate(PERSIAN_DIGITS))
            if min_amt > max_amt:
                raise ValueError("حداقل مبلغ نباید از حداکثر مبلغ بزرگ‌تر باشد.")

            # عوارض‌ها: اگر خالی باشند، منطقی صفر در نظر گرفته می‌شود (UI پیش‌فرض نمایشی ندارد)
            duty60 = float((self.duty60.text() or "0").replace(',', '').translate(PERSIAN_DIGITS))
            duty40 = float((self.duty40.text() or "0").replace(',', '').translate(PERSIAN_DIGITS))
            harmful_pct = self.harmful_pct.text().strip()

            # تولید و نوشتن خروجی
            df_sales, df_rem = generate_sales(
                inv, cust,
                inv_cols, cust_cols,
                inv_no, doc_id,
                min_amt, max_amt,
                date_from, date_to,
                duty60_per_unit=duty60,
                duty45_per_unit=duty40  # پارامتر sales_logic اسمش 45ه، ولی مقدار 40٪ می‌دیم
            ,
                harmful_duty_percent=harmful_pct
            )

            write_output_excel(df_sales, df_rem, self.file_out.text())
            QtWidgets.QMessageBox.information(self, "موفقیت", "خروجی ذخیره شد.")
            # آماده‌سازی نوبت بعد: افزایش خودکار مقادیر
            try:
                _n_inv, _n_doc = load_next_defaults(default_invoice=None)
                if _n_inv is not None:
                    self.inv_no.setText(str(_n_inv))
                self.doc_id.setText(str(_n_doc))
            except Exception:
                pass

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا در اجرا", str(e))


def main():
    app = QtWidgets.QApplication([])
    app.setApplicationName("تولید فاکتور فروش - عباسپور")
    w = SalesPage()
    w.resize(900,400)  # قدّ کوتاه‌تر
    w.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())