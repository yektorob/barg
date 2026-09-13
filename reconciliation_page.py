#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os
import pandas as pd
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui
from ui.widgets import StyledLineEdit, StyledComboBox, StyledButton, inch
from reconciliation_logic import reconcile_with_tolerance, reconcile_shaparak

class ReconciliationPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ReconciliationPage")
        self.setLayoutDirection(QtCore.Qt.RightToLeft)

        # ---------- استایل ----------
        qss = os.path.join(os.path.dirname(__file__), 'styles', 'abbaspoor.qss')
        if os.path.exists(qss):
            with open(qss, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())

        # ---------- چیدمان کلی ----------
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(1)

        h_center = QtWidgets.QHBoxLayout()
        h_center.addStretch(1)

        frame = QtWidgets.QFrame()
        frame.setObjectName("AbbaspoorFrame")
        frame.setMinimumWidth(inch(11))
        h_center.addWidget(frame)
        h_center.addStretch(1)

        outer.addLayout(h_center)
        outer.addStretch(1)

        v = QtWidgets.QVBoxLayout(frame)
        v.setContentsMargins(30, 30, 30, 30)
        v.setSpacing(20)

        # ۱) فایل ورودی
        h1 = QtWidgets.QHBoxLayout(); h1.setSpacing(15)
        self.input_file = StyledLineEdit("فایل ورودی")
        btn_in = StyledButton("انتخاب فایل")
        h1.addWidget(self.input_file, 1); h1.addWidget(btn_in)
        v.addLayout(h1)
        btn_in.clicked.connect(self._choose_input)

        # ۲) شیت بانک
        h2 = QtWidgets.QHBoxLayout(); h2.setSpacing(15)
        lbl2 = QtWidgets.QLabel("شیت بانک:"); lbl2.setStyleSheet("color:#f5f5f5;")
        self.sheet_bank = StyledComboBox("انتخاب شیت بانک")
        h2.addWidget(lbl2); h2.addWidget(self.sheet_bank, 1)
        v.addLayout(h2)
        self.sheet_bank.currentIndexChanged.connect(self._load_columns)

        # ۳) حالت فایل بانک
        h3 = QtWidgets.QHBoxLayout(); h3.setSpacing(15)
        lbl3 = QtWidgets.QLabel("حالت فایل بانک:"); lbl3.setStyleSheet("color:#f5f5f5;")
        self.rb_two  = QtWidgets.QRadioButton("دو ستون جدا")
        self.rb_type = QtWidgets.QRadioButton("مبلغ + نوع تراکنش")
        self.rb_two.setChecked(True)
        grp = QtWidgets.QButtonGroup(self); grp.addButton(self.rb_two); grp.addButton(self.rb_type)
        h3.addWidget(lbl3); h3.addWidget(self.rb_two); h3.addWidget(self.rb_type)
        v.addLayout(h3)
        grp.buttonToggled.connect(self._switch_bank_mapping)

        # ۴) نگاشت ستون‌های بانک (Stacked)
        self.bank_map_stack = QtWidgets.QStackedLayout()
        self._init_bank_mapping()
        v.addLayout(self.bank_map_stack)

        # ۵) نگاشت یاران
        lbl5 = QtWidgets.QLabel("شیت یاران:"); lbl5.setStyleSheet("color:#f5f5f5;")
        v.addWidget(lbl5)
        h5 = QtWidgets.QHBoxLayout(); h5.setSpacing(15)
        self.y_date = StyledComboBox("تاریخ یاران"); self.y_date.setProperty('ph', 'تاریخ یاران')
        self.y_desc = StyledComboBox("شرح یاران");  self.y_desc.setProperty('ph', 'شرح یاران')
        self.y_deb  = StyledComboBox("بدهکار یاران"); self.y_deb.setProperty('ph', 'بدهکار یاران')
        self.y_cre  = StyledComboBox("بستانکار یاران"); self.y_cre.setProperty('ph', 'بستانکار یاران')
        self.y_temp = StyledComboBox("شماره موقت"); self.y_temp.setProperty('ph', 'شماره موقت')
        for cb in (self.y_date, self.y_desc, self.y_deb, self.y_cre, self.y_temp):
            h5.addWidget(cb)
        v.addLayout(h5)

        # ۶) نوع مغایرت و شاپرک
        h6 = QtWidgets.QHBoxLayout(); h6.setSpacing(15)
        self.rb_amt = QtWidgets.QRadioButton("مغایرت مبلغی")
        self.rb_shp = QtWidgets.QRadioButton("مغایرت شاپرکی")
        self.rb_amt.setChecked(True)
        grp2 = QtWidgets.QButtonGroup(self); grp2.addButton(self.rb_amt); grp2.addButton(self.rb_shp)
        lbl_kw = QtWidgets.QLabel("کلمه کلیدی شاپرک:"); lbl_kw.setStyleSheet("color:#f5f5f5;")
        self.keyword = StyledLineEdit("شاپرک")
        h6.addWidget(QtWidgets.QLabel("نوع مغایرت‌گیری:"))
        h6.addWidget(self.rb_amt); h6.addWidget(self.rb_shp)
        h6.addSpacing(20); h6.addWidget(lbl_kw); h6.addWidget(self.keyword, 1)
        v.addLayout(h6)

        # ۶.۵) حالت تاریخ‌محور برای مبلغی — فیلد عددی کوچک
        h6b = QtWidgets.QHBoxLayout(); h6b.setSpacing(12)

        self.cb_datewin = QtWidgets.QCheckBox("تطبیق تاریخ‌")
        self.cb_datewin.setToolTip("اگر فعال باشد: ابتدا همان‌روز جفت‌سازی؛ در صورت عدم تطابق، نزدیک‌ترین تاریخ تا N روز (یک‌به‌یک).")

        lbl_days = QtWidgets.QLabel("بازه:")
        lbl_days.setStyleSheet("color:#e5e7eb;")

        self.edt_datewin = QtWidgets.QLineEdit()
        self.edt_datewin.setObjectName("DaysEdit")
        self.edt_datewin.setValidator(QtGui.QIntValidator(0, 2147483647, self))
        self.edt_datewin.setPlaceholderText("0")
        self.edt_datewin.setText("2")
        self.edt_datewin.setAlignment(QtCore.Qt.AlignCenter)
        self.edt_datewin.setEnabled(False)
        self.edt_datewin.setFixedWidth(72)  # کوچیک مثل بقیه‌ی فیلدها

        lbl_suffix = QtWidgets.QLabel("روز")
        lbl_suffix.setStyleSheet("color:#e5e7eb;")

        h6b.addWidget(self.cb_datewin)
        h6b.addSpacing(8)
        h6b.addWidget(lbl_days)
        h6b.addWidget(self.edt_datewin)
        h6b.addWidget(lbl_suffix)
        h6b.addStretch(1)
        v.addLayout(h6b)

        self.cb_datewin.toggled.connect(self.edt_datewin.setEnabled)

        # استایل هماهنگ با تم
# … بعد از ساخت self.edt_datewin …
        self.setStyleSheet(self.styleSheet() + """
        QLineEdit#DaysEdit {
        padding: 4px 10px;
        border: 1px solid #3b3b3b;
        border-radius: 12px;           /* گردتر */
        background: #1e1e1e;           /* رنگ درخواستی */
        color: #e5e7eb;
        selection-background-color: #334155;
        }
        QLineEdit#DaysEdit:disabled {
        background: #1a1a1a;
        color: #9ca3af;
        border-color: #2a2a2a;
        }
        QLineEdit#DaysEdit:focus {
        border-color: #5b9cff;         /* فیدبک فوکِس ظریف */
        outline: none;
        }
        """)

        # ۷) خروجی
        h7 = QtWidgets.QHBoxLayout(); h7.setSpacing(15)
        self.output_file = StyledLineEdit("فایل خروجی")
        btn_out = StyledButton("انتخاب مسیر")
        h7.addWidget(self.output_file, 1); h7.addWidget(btn_out)
        v.addLayout(h7)
        btn_out.clicked.connect(self._choose_output)

        # ۸) اجرا
        btn_run = StyledButton("مغایرت‌گیری")
        btn_run.setFixedWidth(200)
        v.addWidget(btn_run, 0, QtCore.Qt.AlignCenter)
        btn_run.clicked.connect(self._run)

        # مقدار اولیه
        self._switch_bank_mapping(self.rb_two, True)

    # ---------- بانک: دو حالت نگاشت ----------
    def _init_bank_mapping(self):
        # دو ستون جدا
        w0 = QtWidgets.QWidget(); h0 = QtWidgets.QHBoxLayout(w0); h0.setSpacing(15)
        self.bank_date = StyledComboBox("تاریخ بانک"); self.bank_date.setProperty('ph', 'تاریخ بانک')
        self.bank_desc = StyledComboBox("شرح بانک");  self.bank_desc.setProperty('ph', 'شرح بانک')
        self.bank_debit = StyledComboBox("بدهکار");   self.bank_debit.setProperty('ph', 'بدهکار')
        self.bank_credit = StyledComboBox("بستانکار"); self.bank_credit.setProperty('ph', 'بستانکار')
        for cb in (self.bank_date, self.bank_desc, self.bank_debit, self.bank_credit):
            h0.addWidget(cb)
        self.bank_map_stack.addWidget(w0)

        # مبلغ + نوع تراکنش
        w1 = QtWidgets.QWidget(); h1 = QtWidgets.QHBoxLayout(w1); h1.setSpacing(15)
        self.bank_date2 = StyledComboBox("تاریخ بانک"); self.bank_date2.setProperty('ph', 'تاریخ بانک')
        self.bank_desc2 = StyledComboBox("شرح بانک");   self.bank_desc2.setProperty('ph', 'شرح بانک')
        self.bank_type  = StyledComboBox("نوع تراکنش"); self.bank_type.setProperty('ph', 'نوع تراکنش')
        self.bank_amount= StyledComboBox("مبلغ");       self.bank_amount.setProperty('ph', 'مبلغ')
        for cb in (self.bank_date2, self.bank_desc2, self.bank_type, self.bank_amount):
            h1.addWidget(cb)
        self.bank_map_stack.addWidget(w1)

    def _switch_bank_mapping(self, btn, checked):
        if btn is self.rb_two and checked:
            self.bank_map_stack.setCurrentIndex(0)
        elif btn is self.rb_type and checked:
            self.bank_map_stack.setCurrentIndex(1)

    # ---------- رویدادها ----------
    def _choose_input(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "انتخاب فایل ورودی", "", "Excel Files (*.xlsx *.xls)"
        )
        if fn:
            self.input_file.setText(fn)
            try:
                xl = pd.ExcelFile(fn)
                self.sheet_bank.clear()
                self.sheet_bank.addItems(xl.sheet_names)
                if xl.sheet_names:
                    self.sheet_bank.setCurrentIndex(0)
                    self._load_columns()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "خطا", f"خواندن فایل ناموفق:\n{e}")

    def _load_columns(self):
        try:
            f = self.input_file.text()
            s = self.sheet_bank.currentText()
            if not f or not s:
                return

            cols = pd.read_excel(f, sheet_name=s).columns.astype(str).tolist()
            self._populate_columns(cols, is_bank=True)

            ycols = (
                pd.read_excel(f, sheet_name='یاران')
                .columns.astype(str)
                .str.replace('\u200f','')
                .str.replace('ي','ی')
                .str.replace('ك','ک')
                .tolist()
            )
            self._populate_columns(ycols, is_bank=False)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "⚠️ خطا", f"بارگذاری ستون‌ها ناموفق:\n{e}")

    def _populate_columns(self, columns, is_bank=True):
        if is_bank:
            targets = (
                self.bank_date, self.bank_desc, self.bank_debit, self.bank_credit,
                self.bank_date2, self.bank_desc2, self.bank_type, self.bank_amount
            )
        else:
            targets = (self.y_date, self.y_desc, self.y_deb, self.y_cre, self.y_temp)

        for cb in targets:
            cb.blockSignals(True)
            ph = (cb.property('ph') or "").strip() or "انتخاب کنید"
            cb.clear()
            cb.addItem(ph)
            try:
                mdl = cb.model()
                item0 = mdl.item(0)
                if item0: item0.setEnabled(False)
            except Exception:
                pass
            cb.addItems(columns)
            cb.setCurrentIndex(0)
            cb.blockSignals(False)

    def _choose_output(self):
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "انتخاب مسیر خروجی", "", "Excel Files (*.xlsx)"
        )
        if fn:
            self.output_file.setText(fn)

    def _run(self):
        try:
            def _sel(cb):
                return cb.currentText().strip() if cb.currentIndex() > 0 else ""

            inp     = self.input_file.text()
            sheet   = self.sheet_bank.currentText()
            mode    = 'دو ستون جدا' if self.rb_two.isChecked() else 'مبلغ + نوع تراکنش'

            # بانک
            date    = _sel(self.bank_date)  if self.rb_two.isChecked() else _sel(self.bank_date2)
            desc    = _sel(self.bank_desc)  if self.rb_two.isChecked() else _sel(self.bank_desc2)
            debit   = _sel(self.bank_debit) if self.rb_two.isChecked() else ""
            credit  = _sel(self.bank_credit) if self.rb_two.isChecked() else ""
            amount  = _sel(self.bank_amount) if self.rb_type.isChecked() else ""
            ttype   = _sel(self.bank_type)   if self.rb_type.isChecked() else ""

            # یاران
            ydate   = _sel(self.y_date)
            ydesc   = _sel(self.y_desc)
            ydeb    = _sel(self.y_deb)
            ycre    = _sel(self.y_cre)
            ytemp   = _sel(self.y_temp)

            outp    = self.output_file.text()

            # اعتبارسنجی حداقلی
            if not inp or not os.path.exists(inp):
                QtWidgets.QMessageBox.warning(self, "⚠️", "فایل ورودی انتخاب نشده یا وجود ندارد.")
                return
            if not outp:
                QtWidgets.QMessageBox.warning(self, "⚠️", "مسیر فایل خروجی را انتخاب کنید.")
                return

            if self.rb_two.isChecked():
                needed = [('تاریخ بانک', date), ('شرح بانک', desc), ('بدهکار', debit), ('بستانکار', credit)]
            else:
                needed = [('تاریخ بانک', date), ('شرح بانک', desc), ('نوع تراکنش', ttype), ('مبلغ', amount)]
            miss = [n for n, v in needed if not v]
            if miss:
                QtWidgets.QMessageBox.warning(self, "⚠️", "لطفاً ستون‌های زیر را انتخاب کنید:\n- " + "\n- ".join(miss))
                return

            if not ydate or not ydesc or (not ydeb and not ycre):
                QtWidgets.QMessageBox.warning(
                    self, "⚠️",
                    "برای شیت یاران حداقل «تاریخ»، «شرح» و یکی از «بدهکار/بستانکار» را انتخاب کنید."
                )
                return

            # اجرا
            if self.rb_amt.isChecked():
                use_date = self.cb_datewin.isChecked()
                days_txt = (self.edt_datewin.text() or "0").strip()
                # QIntValidator اجازه می‌دهد: یا خالی یا عدد صحیح
                days = int(days_txt) if (use_date and len(days_txt) > 0) else 0

                reconcile_with_tolerance(
                    input_path=inp,
                    sheet_name=sheet,
                    bank_mode=mode,
                    date_col=date,
                    desc_col=desc,
                    debit_col=debit,
                    credit_col=credit,
                    amount_col=amount,
                    type_col=ttype,
                    yaran_date_col=ydate,
                    yaran_desc_col=ydesc,
                    yaran_debit_col=ydeb,
                    yaran_credit_col=ycre,
                    yaran_tempno_col=ytemp,
                    output_path=outp,
                    tolerance=1.0,
                    use_date_matching=use_date,   # بدون تیک: False (فقط مبلغ)
                    pair_window_days=days,         # با تیک: N روز (عدد کوچک، فیلد جمع‌وجور)
                    log_path=(outp + ".log")
                )
            else:
                reconcile_shaparak(
                    input_path=inp,
                    sheet_name=sheet,
                    date_col=date,
                    desc_col=desc,
                    debit_col=debit,
                    credit_col=credit,
                    amount_col=amount,
                    type_col=ttype,
                    yaran_date_col=ydate,
                    yaran_desc_col=ydesc,
                    yaran_debit_col=ydeb,
                    yaran_credit_col=ycre,
                    yaran_tempno_col=ytemp,
                    output_path=outp,
                    keyword=self.keyword.text().strip()
                )

            # پیام موفقیت
            QtWidgets.QMessageBox.information(self, "✅ انجام شد", f"فایل خروجی ذخیره شد:\n{outp}\n\n📄 گزارش لاگ: {outp}.log")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "❌ خطا", f"خطا در اجرای مغایرت:\n{e}\n\n📄 برای جزئیات، فایل لاگ را ببینید: {outp}.log")

# اجرای مستقل
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qss = os.path.join(os.path.dirname(__file__), 'styles', 'main.qss')
    if os.path.exists(qss):
        with open(qss, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
    win = ReconciliationPage()
    win.show()
    sys.exit(getattr(app, 'exec', getattr(app, 'exec_', lambda: 0))())