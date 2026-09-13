# ffasli_page.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pandas as pd
from PySide6 import QtWidgets, QtGui, QtCore
from ffasli_logic import generate_sales

DPI = 96
def inch(x): return int(x * DPI)

class StyledLineEdit(QtWidgets.QLineEdit):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(40)

class StyledComboBox(QtWidgets.QComboBox):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setEditable(False)
        self.setFixedHeight(40)
        self._bg_color     = QtGui.QColor("#2C2E33")
        self._border_color = QtGui.QColor("#383838")
        self._arrow_bg     = QtGui.QColor("#383838")
        self._arrow_color  = QtGui.QColor("#f5f5f5")

        if placeholder:
            self.addItem(placeholder)
            self.model().item(0).setEnabled(False)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()

        pen = QtGui.QPen(self._border_color, 1)
        painter.setPen(pen)
        painter.setBrush(self._bg_color)
        painter.drawRoundedRect(rect, 20, 20)

        diameter = rect.height() - 8
        circle_rect = QtCore.QRect(4, (rect.height() - diameter)//2, diameter, diameter)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self._arrow_bg)
        painter.drawEllipse(circle_rect)

        cx, cy = circle_rect.center().x(), circle_rect.center().y()
        points = [QtCore.QPoint(cx-4, cy-2), QtCore.QPoint(cx+4, cy-2), QtCore.QPoint(cx, cy+4)]
        painter.setBrush(self._arrow_color)
        painter.drawPolygon(QtGui.QPolygon(points))

        painter.setPen(self._arrow_color)
        text_rect = rect.adjusted(circle_rect.right()+8, 0, -8, 0)
        painter.drawText(text_rect, QtCore.Qt.AlignVCenter, self.currentText())
        painter.end()

class StyledButton(QtWidgets.QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(40)
        self.setCursor(QtCore.Qt.PointingHandCursor)

class AbbaspoorPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AbbaspoorPage")
        self.setLayoutDirection(QtCore.Qt.RightToLeft)

        # بارگذاری استایل عباسپور
        qss_path = os.path.join(os.path.dirname(__file__), 'styles', 'abbaspoor.qss')
        with open(qss_path, 'r', encoding='utf-8') as f:
            self.setStyleSheet(f.read())

        layout_main = QtWidgets.QHBoxLayout(self)
        layout_main.setContentsMargins(0,0,0,0)
        layout_main.setAlignment(QtCore.Qt.AlignCenter)

        frame = QtWidgets.QFrame()
        frame.setObjectName("AbbaspoorFrame")
        frame.setMaximumWidth(inch(10.64))
        layout_main.addWidget(frame)

        v = QtWidgets.QVBoxLayout(frame)
        v.setContentsMargins(30,30,30,30)
        v.setSpacing(20)

        # 1) آپلود فایل
        h1 = QtWidgets.QHBoxLayout(); h1.setSpacing(15)
        self.file_in = StyledLineEdit("فایل ورودی")
        btn_up = StyledButton("آپلود فایل"); btn_up.clicked.connect(self._choose_input)
        h1.addWidget(self.file_in, 1); h1.addWidget(btn_up)
        v.addLayout(h1)

        # 2) شیت‌ها و پارامترها
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(15); grid.setVerticalSpacing(15)

        lbl_inv = QtWidgets.QLabel("شیت موجودی:"); lbl_inv.setStyleSheet("color:#f5f5f5;")
        self.sheet_inv = StyledComboBox("انتخاب شیت موجودی")
        self.inv_no    = StyledLineEdit("شماره فاکتور")
        self.doc_id    = StyledLineEdit("شناسه سند")
        grid.addWidget(lbl_inv, 0,0, alignment=QtCore.Qt.AlignRight)
        grid.addWidget(self.sheet_inv,0,1); grid.addWidget(self.inv_no,0,2); grid.addWidget(self.doc_id,0,3)

        lbl_cust = QtWidgets.QLabel("شیت مشتری:"); lbl_cust.setStyleSheet("color:#f5f5f5;")
        self.sheet_cust = StyledComboBox("انتخاب شیت مشتری")
        self.min_amt     = StyledLineEdit("حداقل مبلغ فاکتور")
        self.max_amt     = StyledLineEdit("حداکثر مبلغ فاکتور")
        grid.addWidget(lbl_cust,1,0, alignment=QtCore.Qt.AlignRight)
        grid.addWidget(self.sheet_cust,1,1); grid.addWidget(self.min_amt,1,2); grid.addWidget(self.max_amt,1,3)

        grid.setColumnStretch(1,1); grid.setColumnStretch(2,1); grid.setColumnStretch(3,1)
        v.addLayout(grid)

        self.inv_map, self.cust_map = {}, {}
        self.sheet_inv.currentTextChanged.connect(self._load_inv_cols)
        self.sheet_cust.currentTextChanged.connect(self._load_cust_cols)

        # 3) گروه‌باکس ستون‌ها
        hb = QtWidgets.QHBoxLayout(); hb.setSpacing(15)
        inv_box  = QtWidgets.QGroupBox("ستون‌های موجودی");  inv_form  = QtWidgets.QFormLayout(inv_box)
        cust_box = QtWidgets.QGroupBox("ستون‌های مشتری"); cust_form = QtWidgets.QFormLayout(cust_box)
        inv_form.setContentsMargins(10,30,10,10); cust_form.setContentsMargins(10,30,10,10)
        for lbl, key in [("کد کالا","code"),("نام کالا","name"),("قیمت","price"),
                         ("موجودی","quantity"),("تاریخ","date")]:
            cb = StyledComboBox(); inv_form.addRow(lbl+":",cb); self.inv_map[key]=cb
        for lbl, key in [("کد مشتری","code"),("نام مشتری","name")]:
            cb = StyledComboBox(); cust_form.addRow(lbl+":",cb); self.cust_map[key]=cb
        hb.addWidget(inv_box,1); hb.addWidget(cust_box,1); v.addLayout(hb)

        # 4) فایل خروجی
        h4 = QtWidgets.QHBoxLayout(); h4.setSpacing(15)
        self.file_out = StyledLineEdit("فایل خروجی")
        btn_out = StyledButton("انتخاب مسیر"); btn_out.clicked.connect(self._choose_output)
        h4.addWidget(self.file_out,1); h4.addWidget(btn_out); v.addLayout(h4)

        # 5) دکمه نهایی
        btn_run = StyledButton("ایجاد و ذخیره"); btn_run.setFixedWidth(200)
        btn_run.clicked.connect(self._run); v.addWidget(btn_run,0,QtCore.Qt.AlignCenter)

    def _choose_input(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "انتخاب فایل Excel", "", "Excel Files (*.xlsx)")
        if not path: return
        self.file_in.setText(path)
        try:
            sheets = pd.ExcelFile(path).sheet_names
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", str(e)); return
        self.sheet_inv.clear(); self.sheet_inv.addItems(sheets)
        self.sheet_cust.clear(); self.sheet_cust.addItems(sheets)

    def _load_inv_cols(self, sheet):
        path = self.file_in.text()
        if not path or sheet.startswith("انتخاب"): return
        try:
            cols = pd.read_excel(path, sheet_name=sheet, nrows=0).columns.tolist()
        except:
            cols = []
        for cb in self.inv_map.values():
            cb.clear(); cb.addItems(cols)

    def _load_cust_cols(self, sheet):
        path = self.file_in.text()
        if not path or sheet.startswith("انتخاب"): return
        try:
            cols = pd.read_excel(path, sheet_name=sheet, nrows=0).columns.tolist()
        except:
            cols = []
        for cb in self.cust_map.values():
            cb.clear(); cb.addItems(cols)

    def _choose_output(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "انتخاب مسیر خروجی", "", "Excel Files (*.xlsx)")
        if path:
            self.file_out.setText(path)

    def _run(self):
        try:
            inv  = pd.read_excel(self.file_in.text(),   sheet_name=self.sheet_inv.currentText())
            cust = pd.read_excel(self.file_in.text(),   sheet_name=self.sheet_cust.currentText())
            inv_cols  = {k:cb.currentText() for k,cb in self.inv_map.items()}
            cust_cols = {k:cb.currentText() for k,cb in self.cust_map.items()}
            df_out = generate_sales(
                inv, cust, inv_cols, cust_cols,
                int(self.inv_no.text()),
                int(self.doc_id.text()),
                int(self.min_amt.text()),
                int(self.max_amt.text())
            )
            df_out.to_excel(self.file_out.text(), index=False)
            QtWidgets.QMessageBox.information(self, "موفقیت", "خروجی ذخیره شد.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", str(e))