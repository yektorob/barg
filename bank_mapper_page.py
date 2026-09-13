# bank_mapper_page.py
# -*- coding: utf-8 -*-

import os
import pandas as pd
from PySide6 import QtWidgets, QtCore

# استفاده از ویجت‌های استایل‌دار عباسپور
from ui.widgets import StyledLineEdit, StyledComboBox, StyledButton, inch
from bank_mapper_logic import process_banks

class BankRow(QtWidgets.QFrame):
    removed = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BankRow")
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.file_path = ""

        v = QtWidgets.QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(10)

        # بالا: آپلود و حذف
        htop = QtWidgets.QHBoxLayout(); htop.setSpacing(10)
        self.file_in = StyledLineEdit("فایل بانک")
        try: self.file_in.setPlaceholderText("")
        except Exception: pass
        btn_up = StyledButton("آپلود فایل"); btn_up.clicked.connect(self._choose_input)
        btn_rm = StyledButton("حذف"); btn_rm.clicked.connect(lambda: self.removed.emit(self))
        htop.addWidget(self.file_in, 1); htop.addWidget(btn_up); htop.addWidget(btn_rm)
        v.addLayout(htop)

        # ردیف واحد: همه‌ی کمبوها + کدها کنار هم
        grid = QtWidgets.QGridLayout(); grid.setHorizontalSpacing(12); grid.setVerticalSpacing(0)

        self.sheet_cb = StyledComboBox("انتخاب شیت")
        self.col_date = StyledComboBox("ستون تاریخ")
        self.col_desc = StyledComboBox("ستون شرح")
        self.col_dep  = StyledComboBox("ستون واریز")
        self.col_wdr  = StyledComboBox("ستون برداشت")
        self.tafta_in = StyledLineEdit("کد تفضیلی طرفِ بانک")
        self.fee_code = StyledLineEdit("کد کارمزد بانک")

        # فقط LineEditها بدون placeholder
        for w in (self.tafta_in, self.fee_code):
            try: w.setPlaceholderText("")
            except Exception: pass
        # به کمبوها دست نمی‌زنیم

        pairs = [
            ("شیت:", self.sheet_cb),
            ("تاریخ:", self.col_date),
            ("شرح:", self.col_desc),
            ("واریز:", self.col_dep),
            ("برداشت:", self.col_wdr),
            ("کد تفضیلی:", self.tafta_in),
            ("کد کارمزد:", self.fee_code),
        ]

        c = 0
        for text, w in pairs:
            lab = QtWidgets.QLabel(text); lab.setObjectName("Label")
            grid.addWidget(lab, 0, c, alignment=QtCore.Qt.AlignRight); c += 1
            grid.addWidget(w,   0, c); c += 1

        for i in range(c):
            if i % 2 == 1:
                grid.setColumnStretch(i, 1)

        v.addLayout(grid)

    def _choose_input(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "انتخاب فایل Excel", "", "Excel Files (*.xlsx)")
        if not path: return
        self.file_path = path
        self.file_in.setText(path)
        try:
            xls = pd.ExcelFile(path)
            self.sheet_cb.clear(); self.sheet_cb.addItems(xls.sheet_names)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا در باز کردن فایل", str(e))

    def _load_columns(self):
        sheet = self.sheet_cb.currentText().strip()
        if not (self.file_path and sheet):
            return
        try:
            df = pd.read_excel(self.file_path, sheet_name=sheet, nrows=0)
            cols = [str(c).strip() for c in df.columns.tolist()]
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا در خواندن شیت", str(e))
            return
        for cb in (self.col_date, self.col_desc, self.col_dep, self.col_wdr):
            cb.clear(); cb.addItems(cols)

    def get_payload(self):
        need = [self.file_path, self.sheet_cb.currentText().strip(),
                self.col_date.currentText().strip(),
                self.col_desc.currentText().strip(),
                self.col_dep.currentText().strip(),
                self.col_wdr.currentText().strip()]
        if not all(need):
            raise ValueError("فایل/شیت/ستون‌ها کامل انتخاب نشده‌اند.")

        try:
            df = pd.read_excel(self.file_path, sheet_name=self.sheet_cb.currentText().strip())
        except Exception as e:
            raise ValueError(f"خطا در خواندن شیت: {e}")

        vals = {
            "تاریخ": self.col_date.currentText().strip(),
            "شرح": self.col_desc.currentText().strip(),
            "واریز": self.col_dep.currentText().strip(),
            "برداشت": self.col_wdr.currentText().strip(),
            "کد تفضیلی": self.tafta_in.text().strip(),
            "کد کارمزد": self.fee_code.text().strip(),
        }
        return {"df": df, "vals": vals}

    def connect_signals(self):
        self.sheet_cb.currentTextChanged.connect(lambda _: self._load_columns())


class BankMapperPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BankMapperPage")
        self.setLayoutDirection(QtCore.Qt.RightToLeft)

        qss = os.path.join(os.path.dirname(__file__), "styles", "abbaspoor.qss")
        if os.path.exists(qss):
            with open(qss, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(1)

        h_center = QtWidgets.QHBoxLayout()
        h_center.addStretch(1)

        frame = QtWidgets.QFrame()
        frame.setObjectName("AbbaspoorFrame")
        frame.setMinimumWidth(inch(13.5))
        frame.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)

        h_center.addWidget(frame)
        h_center.addStretch(1)

        outer.addLayout(h_center)
        outer.addStretch(1)

        v = QtWidgets.QVBoxLayout(frame)
        v.setContentsMargins(30,30,30,30)
        v.setSpacing(18)

        # ردیف بالایی
        top_grid = QtWidgets.QGridLayout(); top_grid.setHorizontalSpacing(12); top_grid.setVerticalSpacing(0)

        self.start_doc = StyledLineEdit("شماره سند شروع")
        self.start_id  = StyledLineEdit("شناسه شروع")
        self.default_fee = StyledLineEdit("کد کارمزد (پیش‌فرض)")

        for w in (self.start_doc, self.start_id, self.default_fee):
            try: w.setPlaceholderText("")
            except Exception: pass

        top_pairs = [
            ("شماره سند شروع:", self.start_doc),
            ("شناسه شروع:", self.start_id),
            ("کد کارمزد (پیش‌فرض):", self.default_fee),
        ]

        c = 0
        for text, w in top_pairs:
            lab = QtWidgets.QLabel(text); lab.setObjectName("Label")
            top_grid.addWidget(lab, 0, c, alignment=QtCore.Qt.AlignRight); c += 1
            top_grid.addWidget(w,   0, c); c += 1

        for i in range(c):
            if i % 2 == 1:
                top_grid.setColumnStretch(i, 1)

        v.addLayout(top_grid)

        # ناحیه بانک‌ها
        self.bank_area = QtWidgets.QScrollArea()
        self.bank_area.setWidgetResizable(True)
        self.bank_area.setMinimumHeight(inch(3.5))
        wrap = QtWidgets.QWidget()
        self.bank_layout = QtWidgets.QVBoxLayout(wrap); self.bank_layout.setContentsMargins(0,0,0,0); self.bank_layout.setSpacing(12)
        self.bank_area.setWidget(wrap)
        v.addWidget(self.bank_area, 1)

        # دکمه‌های مدیریت بانک‌ها
        hbtn_banks = QtWidgets.QHBoxLayout(); hbtn_banks.setSpacing(12)
        btn_add = StyledButton("بانک جدید"); btn_add.clicked.connect(self._add_bank)
        btn_del = StyledButton("حذف آخرین بانک"); btn_del.clicked.connect(self._remove_last)
        hbtn_banks.addStretch(1); hbtn_banks.addWidget(btn_add); hbtn_banks.addWidget(btn_del); hbtn_banks.addStretch(1)
        v.addLayout(hbtn_banks)

        # مسیر فایل خروجی
        out_grid = QtWidgets.QGridLayout(); out_grid.setHorizontalSpacing(12); out_grid.setVerticalSpacing(0)

        self.output    = StyledLineEdit("مسیر فایل خروجی")
        try: self.output.setPlaceholderText("")
        except Exception: pass
        btn_out = StyledButton("انتخاب مسیر"); btn_out.clicked.connect(self._choose_output)

        out_lab = QtWidgets.QLabel("مسیر فایل خروجی:"); out_lab.setObjectName("Label")
        out_grid.addWidget(out_lab, 0, 0, alignment=QtCore.Qt.AlignRight)
        out_grid.addWidget(self.output, 0, 1)
        out_grid.addWidget(btn_out, 0, 2)

        out_grid.setColumnStretch(1, 1)
        v.addLayout(out_grid)

        # دکمه پردازش
        hbtn_run = QtWidgets.QHBoxLayout(); hbtn_run.setSpacing(12)
        btn_run = StyledButton("پردازش و ذخیره"); btn_run.clicked.connect(self._run)
        hbtn_run.addStretch(1); hbtn_run.addWidget(btn_run)
        v.addLayout(hbtn_run)

        # حداقل یک بانک
        self.bank_rows: list[BankRow] = []
        self._add_bank()

    def _add_bank(self):
        row = BankRow()
        row.connect_signals()
        row.removed.connect(self._remove_row)
        self.bank_rows.append(row)
        self.bank_layout.addWidget(row)

    def _remove_row(self, row):
        if row in self.bank_rows:
            self.bank_rows.remove(row)
            row.setParent(None); row.deleteLater()

    def _remove_last(self):
        if len(self.bank_rows) > 1:
            row = self.bank_rows.pop()
            row.setParent(None); row.deleteLater()

    def _choose_output(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "ذخیره به Excel", "", "Excel Files (*.xlsx)")
        if path:
            if not path.lower().endswith('.xlsx'):
                path += '.xlsx'
            self.output.setText(path)

    def _run(self):
        try:
            start_doc = int(self.start_doc.text().strip())
            start_id  = int(self.start_id.text().strip())
        except Exception:
            QtWidgets.QMessageBox.critical(self, "خطا", "شماره سند و شناسه باید عدد باشند.")
            return

        default_fee = self.default_fee.text().strip()
        out_path = self.output.text().strip()
        if not out_path:
            QtWidgets.QMessageBox.warning(self, "کمبود مسیر خروجی", "لطفاً مسیر خروجی را انتخاب کن.")
            return

        banks = []
        try:
            for r in self.bank_rows:
                banks.append(r.get_payload())
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", str(e))
            return

        try:
            df_out, bad_cnt = process_banks(banks, start_doc, start_id, out_path, default_fee)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", str(e))
            return

        try:
            with pd.ExcelWriter(out_path, engine='xlsxwriter', datetime_format='yyyy-mm-dd', date_format='yyyy-mm-dd') as writer:
                df_out.to_excel(writer, index=False, sheet_name='Sheet1')
                ws = writer.sheets['Sheet1']
                if hasattr(ws, 'right_to_left'):
                    ws.right_to_left()
                else:
                    try:
                        ws.sheet_view.rightToLeft = True
                    except Exception:
                        pass
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا در ذخیره", str(e))
            return

        msg = "فایل خروجی با موفقیت ذخیره شد."
        if bad_cnt:
            msg += f" ({bad_cnt} ردیف با تاریخ نامعتبر حذف شد)"
        QtWidgets.QMessageBox.information(self, "موفقیت", msg)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    qss = os.path.join(os.path.dirname(__file__), "styles", "abbaspoor.qss")
    if os.path.exists(qss):
        with open(qss, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    w = BankMapperPage()
    w.adjustSize()
    w.show()
    app.exec()