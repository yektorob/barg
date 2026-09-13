# abbaspoor_page.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pandas as pd
from PySide6 import QtWidgets, QtGui, QtCore
from abbaspoor_logic import generate_sales, build_daily_diff, build_remaining_inventory_sheet

try:
    from abbaspoor_logic import generate_sales as generate_sales_shaparak
except Exception:
    generate_sales_shaparak = None


DPI = 96
def inch(x): return int(x * DPI)

class StyledLineEdit(QtWidgets.QLineEdit):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(40)
        self.setStyleSheet("""
            QLineEdit {
                color: #f5f5f5; background-color: #2C2E33;
                border: 1px solid #383838; border-radius: 20px;
                padding-right: 12px;
            }
        """)

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

        # بارگذاری استایل عباسپور (از ui.widgets مرکزی)
        try:
            from ui.widgets import apply_abbaspoor_qss
            apply_abbaspoor_qss(self)
        except Exception:
            # fallback to direct qss if helper unavailable
            try:
                qss_path = os.path.join(os.path.dirname(__file__), 'styles', 'abbaspoor.qss')
                if os.path.exists(qss_path):
                    with open(qss_path, 'r', encoding='utf-8') as f:
                        self.setStyleSheet(f.read())
            except Exception:
                pass

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
        grid.addWidget(lbl_cust,1,0, alignment=QtCore.Qt.AlignRight)
        grid.addWidget(self.sheet_cust,1,1)

        # حداقل و حداکثر برای شاپرک
        lbl_shap_amt = QtWidgets.QLabel("محدوده شاپرک:"); lbl_shap_amt.setStyleSheet("color:#f5f5f5;")
        self.min_amt_shap = StyledLineEdit("حداقل مبلغ شاپرک")
        self.max_amt_shap = StyledLineEdit("حداکثر مبلغ شاپرک")
        grid.addWidget(lbl_shap_amt,2,0, alignment=QtCore.Qt.AlignRight)
        grid.addWidget(self.min_amt_shap,2,1); grid.addWidget(self.max_amt_shap,2,2)

        # حداقل و حداکثر برای انتقالی
        lbl_transfer_amt = QtWidgets.QLabel("محدوده انتقالی:"); lbl_transfer_amt.setStyleSheet("color:#f5f5f5;")
        self.min_amt_transfer = StyledLineEdit("حداقل مبلغ انتقالی")
        self.max_amt_transfer = StyledLineEdit("حداکثر مبلغ انتقالی")
        grid.addWidget(lbl_transfer_amt,3,0, alignment=QtCore.Qt.AlignRight)
        grid.addWidget(self.min_amt_transfer,3,1); grid.addWidget(self.max_amt_transfer,3,2)

        # --- شاپرک: انتخاب شیت ---
        lbl_shap = QtWidgets.QLabel("شیت شاپرک:"); lbl_shap.setStyleSheet("color:#f5f5f5;")
        self.sheet_shap = StyledComboBox("انتخاب شیت شاپرک")
        grid.addWidget(lbl_shap,4,0, alignment=QtCore.Qt.AlignRight)
        grid.addWidget(self.sheet_shap,4,1)

        grid.setColumnStretch(1,1); grid.setColumnStretch(2,1); grid.setColumnStretch(3,1)
        v.addLayout(grid)

        self.inv_map, self.cust_map = {}, {}
        self.sheet_inv.currentTextChanged.connect(self._load_inv_cols)
        self.sheet_cust.currentTextChanged.connect(self._load_cust_cols)
        # شاپرک: اتصال بارگذاری ستون‌ها
        try:
            self.sheet_shap.currentTextChanged.connect(self._load_shap_cols)
        except Exception:
            pass

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
        hb.addWidget(inv_box,1); hb.addWidget(cust_box,1);

        # شاپرک: گروه‌باکس ستون‌ها
        shap_box = QtWidgets.QGroupBox("ستون‌های شاپرک"); shap_form = QtWidgets.QFormLayout(shap_box)
        self.shap_map = {}
        for lbl, key in [
            ("تاریخ (شاپرک)",   "date"),
            ("بستانکار (شاپرک)", "credit"),
            ("نوع (شاپرک)",     "type"),
        ]:
            cb = StyledComboBox()
            shap_form.addRow(lbl + ":", cb)
            self.shap_map[key] = cb
        hb.addWidget(shap_box, 1)
        v.addLayout(hb)

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
        try:
            self.sheet_shap.clear(); self.sheet_shap.addItems(sheets)
        except Exception:
            pass

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

    def _load_shap_cols(self, sheet):
        path = self.file_in.text()
        if not path or sheet.startswith("انتخاب"): return
        try:
            cols = pd.read_excel(path, sheet_name=sheet, nrows=0).columns.tolist()
        except:
            cols = []
        for cb in self.shap_map.values():
            cb.clear(); cb.addItems(cols)

    def _choose_output(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "انتخاب مسیر خروجی", "", "Excel Files (*.xlsx)")
        if path:
            self.file_out.setText(path)

    def _run(self):
        # تلاش برای تولید بر اساس «شاپرک» (اگر ماژول جدید موجود است)
        if 'generate_sales_shaparak' in globals() and generate_sales_shaparak is not None:
            try:
                inv  = pd.read_excel(self.file_in.text(),   sheet_name=self.sheet_inv.currentText())
                cust = pd.read_excel(self.file_in.text(),   sheet_name=self.sheet_cust.currentText())
                shap = pd.read_excel(self.file_in.text(), sheet_name=self.sheet_shap.currentText())
                inv_cols  = {k: cb.currentText() for k, cb in self.inv_map.items()}
                cust_cols = {k: cb.currentText() for k, cb in self.cust_map.items()}
                shap_cols = {k: cb.currentText() for k, cb in self.shap_map.items()}

                # خواندن مقادیر جداگانه برای شاپرک و انتقالی
                min_shap = int(self.min_amt_shap.text()) if self.min_amt_shap.text().strip() else None
                max_shap = int(self.max_amt_shap.text()) if self.max_amt_shap.text().strip() else None
                min_transfer = int(self.min_amt_transfer.text()) if self.min_amt_transfer.text().strip() else None
                max_transfer = int(self.max_amt_transfer.text()) if self.max_amt_transfer.text().strip() else None

                # اگر ستون نوع در شیت شاپرک وجود نداشت، از مپ حذفش کن
                if 'type' in shap_cols and shap_cols['type'] not in shap.columns:
                    shap_cols.pop('type')
                    
                df_out2 = generate_sales_shaparak(
                    inv, cust, shap,
                    inv_cols, cust_cols, shap_cols,
                    int(self.inv_no.text()), int(self.doc_id.text()),
                    min_shap, max_shap,  # برای شاپرک
                    min_transfer, max_transfer  # برای انتقالی
                )

                # ساخت شیت اختلاف روزانه شاپرک و فاکتورها
                try:
                    df_diff = build_daily_diff(df_out2, shap, shap_cols)
                except Exception:
                    df_diff = None

                # نوشتن در چند شیت
                with pd.ExcelWriter(self.file_out.text(), engine='xlsxwriter') as writer:
                    df_out2.to_excel(writer, sheet_name='فروش', index=False)
                    # شیت موجودی باقیمانده
                    try:
                        rem = build_remaining_inventory_sheet(inv, df_out2, inv_cols)
                        rem.to_excel(writer, sheet_name='موجودی باقیمانده', index=False)
                    except Exception:
                        pass
                    # شیت اختلاف روزانه
                    if df_diff is not None:
                        df_diff.to_excel(writer, sheet_name='اختلاف روزانه', index=False)

                QtWidgets.QMessageBox.information(self, "موفقیت", "خروجی (شاپرک) ذخیره شد.")
                return
            except Exception as e:
                # اگر شاپرک/ماژول یا نگاشت‌ها مشکل داشت، می‌افتیم روی منطق قبلی
                pass

        try:
            inv  = pd.read_excel(self.file_in.text(),   sheet_name=self.sheet_inv.currentText())
            cust = pd.read_excel(self.file_in.text(),   sheet_name=self.sheet_cust.currentText())
            inv_cols  = {k:cb.currentText() for k,cb in self.inv_map.items()}
            cust_cols = {k:cb.currentText() for k,cb in self.cust_map.items()}

            df_out = generate_sales(
                inv, cust, inv_cols, cust_cols,
                int(self.inv_no.text()),
                int(self.doc_id.text()),
                None, None  # بدون محدودیت در حالت fallback
            )

            # نوشتن چند شیت: فروش + موجودی باقیمانده
            with pd.ExcelWriter(self.file_out.text(), engine='xlsxwriter') as writer:
                df_out.to_excel(writer, index=False)
                try:
                    rem = build_remaining_inventory_sheet(inv, df_out, inv_cols)
                    rem.to_excel(writer, sheet_name='موجودی باقیمانده', index=False)
                except Exception:
                    pass

            QtWidgets.QMessageBox.information(self, "موفقیت", "خروجی ذخیره شد.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", str(e))