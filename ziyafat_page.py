# ziyafat_page.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os
from PySide6 import QtWidgets, QtCore
from ui.widgets import StyledLineEdit, StyledButton, inch
from ziyafat_logic import process_ziyafat, load_next_defaults  # ← مهم

class ZiyafatPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ZiyafatPage")
        self.setLayoutDirection(QtCore.Qt.RightToLeft)

        # بارگذاری QSS عباسپور
        qss_p = os.path.join(os.path.dirname(__file__), 'styles', 'abbaspoor.qss')
        if os.path.exists(qss_p):
            with open(qss_p, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())

        # چیدمان مرکزی
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0,0,0,0)
        outer.addStretch(1)
        mh = QtWidgets.QHBoxLayout()
        mh.addStretch(1)
        frame = QtWidgets.QFrame(); frame.setObjectName("AbbaspoorFrame")
        frame.setMinimumWidth(inch(11))
        mh.addWidget(frame); mh.addStretch(1)
        outer.addLayout(mh); outer.addStretch(1)

        v = QtWidgets.QVBoxLayout(frame)
        v.setContentsMargins(30,30,30,30); v.setSpacing(20)

        # 1) فایل سالن
        h1 = QtWidgets.QHBoxLayout(); h1.setSpacing(15)
        self.file_saloon = StyledLineEdit("فایل سالن")
        btn1 = StyledButton("انتخاب فایل سالن")
        h1.addWidget(self.file_saloon,1); h1.addWidget(btn1)
        v.addLayout(h1)
        btn1.clicked.connect(lambda: self._choose_file(self.file_saloon))

        # 2) فایل بیرون‌بر
        h2 = QtWidgets.QHBoxLayout(); h2.setSpacing(15)
        self.file_biroonbar = StyledLineEdit("فایل بیرون‌بر")
        btn2 = StyledButton("انتخاب فایل بیرون‌بر")
        h2.addWidget(self.file_biroonbar,1); h2.addWidget(btn2)
        v.addLayout(h2)
        btn2.clicked.connect(lambda: self._choose_file(self.file_biroonbar))

        # 3) فایل معادل‌سازی مشتری
        h3 = QtWidgets.QHBoxLayout(); h3.setSpacing(15)
        self.file_moadele = StyledLineEdit("فایل معادل‌سازی مشتری")
        btn3 = StyledButton("انتخاب فایل معادل‌سازی")
        h3.addWidget(self.file_moadele,1); h3.addWidget(btn3)
        v.addLayout(h3)
        btn3.clicked.connect(lambda: self._choose_file(self.file_moadele))

        # 4) تنظیمات شناسه و سریال
        h4 = QtWidgets.QHBoxLayout(); h4.setSpacing(15)
        lbl_id = QtWidgets.QLabel("شناسه:");        lbl_id.setStyleSheet("color:#f5f5f5;")
        lbl_serial = QtWidgets.QLabel("شماره سریال:"); lbl_serial.setStyleSheet("color:#f5f5f5;")
        self.entry_id = StyledLineEdit("")       # مقداردهی از state (نه مقدار ثابت)
        self.entry_serial = StyledLineEdit("")
        h4.addWidget(lbl_id);     h4.addWidget(self.entry_id,1)
        h4.addWidget(lbl_serial); h4.addWidget(self.entry_serial,1)
        v.addLayout(h4)

        # 5) مسیر خروجی
        h5 = QtWidgets.QHBoxLayout(); h5.setSpacing(15)
        self.output_file = StyledLineEdit("فایل خروجی")
        btn_out = StyledButton("انتخاب مسیر خروجی")
        h5.addWidget(self.output_file,1); h5.addWidget(btn_out)
        v.addLayout(h5)
        btn_out.clicked.connect(self._choose_output)

        # 6) دکمه‌ی اجرا
        btn_run = StyledButton("تولید فایل خروجی")
        btn_run.setFixedWidth(200)
        v.addWidget(btn_run, 0, QtCore.Qt.AlignCenter)
        btn_run.clicked.connect(self._run)

        # ← مقداردهی اولیه از state (next_id / next_serial)
        self._fill_defaults_from_state()

    # ---------------- Helpers ----------------
    def _fill_defaults_from_state(self):
        try:
            next_id, next_serial = load_next_defaults()
        except Exception:
            next_id, next_serial = 1404000000, 1
        self.entry_id.setText(str(next_id))
        self.entry_serial.setText(str(next_serial))

    def _choose_file(self, widget: StyledLineEdit):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "انتخاب فایل", "", "Excel Files (*.xlsx *.xls)"
        )
        if fn:
            widget.setText(fn)

    def _choose_output(self):
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "ذخیره خروجی", "", "Excel Files (*.xlsx)"
        )
        if fn:
            if not fn.lower().endswith(".xlsx"):
                fn += ".xlsx"
            self.output_file.setText(fn)

    # ---------------- Run ----------------
    def _run(self):
        try:
            # اعتبارسنجی ساده
            sal = self.file_saloon.text().strip()
            bir = self.file_biroonbar.text().strip()
            moa = self.file_moadele.text().strip()
            out = self.output_file.text().strip()

            for p, title in [(sal,"فایل سالن"), (bir,"فایل بیرون‌بر"), (moa,"فایل معادل‌سازی")]:
                if not p or not os.path.isfile(p):
                    raise ValueError(f"{title} انتخاب نشده یا وجود ندارد.")

            if not out:
                raise ValueError("مسیر فایل خروجی را انتخاب کنید.")

            # اعداد
            try:
                start_id = int(self.entry_id.text())
                start_serial = int(self.entry_serial.text())
            except ValueError:
                raise ValueError("مقادیر «شناسه» و «شماره سریال» باید عددی باشند.")

            # اجرا
            process_ziyafat(
                file_saloon=sal,
                file_biroonbar=bir,
                file_moadele=moa,
                start_id=start_id,
                start_serial=start_serial,
                output_path=out
            )

            QtWidgets.QMessageBox.information(self, "موفقیت", "فایل خروجی ذخیره شد.")

            # پس از موفقیت: state به‌روز شده؛ ورودی‌ها را با next+1 پر کن
            self._fill_defaults_from_state()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", str(e))

# --- تست مستقل صفحه ---
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qm = os.path.join(os.path.dirname(__file__), 'styles','main.qss')
    if os.path.exists(qm):
        with open(qm,'r',encoding='utf-8') as f:
            app.setStyleSheet(f.read())
    w = ZiyafatPage()
    w.show()
    sys.exit(app.exec())