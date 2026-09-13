# widgets/bodavi_panel.py
# -*- coding: utf-8 -*-
import jdatetime
from PySide6.QtWidgets import (
    QWidget, QGroupBox, QFormLayout, QLineEdit, QHBoxLayout,
    QRadioButton, QLabel
)
from PySide6.QtCore import Qt

def _valid_jalali(s: str) -> bool:
    try:
        jdatetime.datetime.strptime(s, "%Y/%m/%d")
        return True
    except Exception:
        return False

class BodaviPanel(QGroupBox):
    """
    پنل هیأت بدوی (بدون هیچ فیلدی از تجدیدنظر).
    - تاریخ جلسه هیأت تجدید نظر در این پنل وجود ندارد.
    - منطق فعال/غیرفعال و ریست آبشاری مطابق سناریوهای نهایی.
    """
    def __init__(self, parent=None):
        super().__init__("جزئیات هیأت بدوی")
        # برای انطباق با QSS عباسپور (تیتر راست‌به‌چپ، استایل‌ها…)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setProperty("rtl", "true")
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        form = QFormLayout(self)

        # تاریخ جلسه هیأت بدوی
        self.refer_date = QLineEdit()
        self.refer_date.setInputMask("0000/00/00;_")
        form.addRow("تاریخ جلسه هیأت بدوی:", self.refer_date)

        # نیاز به تحقیق و کارشناسی
        self.invest_box = QGroupBox("نیاز به تحقیق و کارشناسی؟")
        self.invest_box.setLayoutDirection(Qt.RightToLeft)
        self.invest_box.setProperty("rtl", "true")
        h_inv = QHBoxLayout(self.invest_box)
        self.invest_yes = QRadioButton("بله")
        self.invest_no  = QRadioButton("خیر")
        h_inv.addWidget(self.invest_yes)
        h_inv.addWidget(self.invest_no)
        form.addRow(self.invest_box)

        # تاریخ صدور قرار کارشناسی
        self.expert_order_date = QLineEdit()
        self.expert_order_date.setInputMask("0000/00/00;_")
        form.addRow("تاریخ صدور قرار کارشناسی:", self.expert_order_date)

        # تاریخ صدور رأی بدوی
        self.verdict_date = QLineEdit()
        self.verdict_date.setInputMask("0000/00/00;_")
        form.addRow("تاریخ صدور رأی هیأت بدوی:", self.verdict_date)

        # مهلت اعتراض (20 روزه)
        self.objection_deadline = QLineEdit()
        self.objection_deadline.setReadOnly(True)
        form.addRow("مهلت اعتراض به رأی بدوی:", self.objection_deadline)

        # اعتراض شده؟
        self.obj_box = QGroupBox("اعتراض به رأی بدوی انجام شده؟")
        self.obj_box.setLayoutDirection(Qt.RightToLeft)
        self.obj_box.setProperty("rtl", "true")
        h_obj = QHBoxLayout(self.obj_box)
        self.obj_yes = QRadioButton("بله")
        self.obj_no  = QRadioButton("خیر")
        h_obj.addWidget(self.obj_yes)
        h_obj.addWidget(self.obj_no)
        form.addRow(self.obj_box)

        # تاریخ اعتراض
        self.objection_date = QLineEdit()
        self.objection_date.setInputMask("0000/00/00;_")
        form.addRow("تاریخ اعتراض به رأی:", self.objection_date)

        # رأی هیأت بدوی (بدون «رد کامل»)
        self.verdict_box = QGroupBox("رأی هیأت بدوی")
        self.verdict_box.setLayoutDirection(Qt.RightToLeft)
        self.verdict_box.setProperty("rtl", "true")
        h_ver = QHBoxLayout(self.verdict_box)
        self.v_approve = QRadioButton("تایید")
        self.v_adjust  = QRadioButton("تعدیل")
        h_ver.addWidget(self.v_approve)
        h_ver.addWidget(self.v_adjust)
        form.addRow(self.verdict_box)

        # اتصال سیگنال‌ها
        self.refer_date.textChanged.connect(self._on_refer_date_changed)
        self.invest_yes.toggled.connect(self._on_invest_changed)
        self.invest_no.toggled.connect(self._on_invest_changed)
        self.verdict_date.textChanged.connect(self._on_verdict_date_changed)
        self.obj_yes.toggled.connect(self._on_obj_changed)
        self.obj_no.toggled.connect(self._on_obj_changed)

        # حالت اولیه
        self.reset(disable_all=True)

    # ---------- States ----------
    def start(self):
        """وقتی از MainWindow فعال شد، فقط تاریخ جلسه بدوی باز باشد."""
        self.reset(disable_all=False)

    def reset(self, disable_all: bool = True):
        # پاک‌سازی
        self.refer_date.clear()
        self.invest_yes.setChecked(False)
        self.invest_no.setChecked(False)
        self.expert_order_date.clear()
        self.verdict_date.clear()
        self.objection_deadline.clear()
        self.obj_yes.setChecked(False)
        self.obj_no.setChecked(False)
        self.objection_date.clear()
        self.v_approve.setChecked(False)
        self.v_adjust.setChecked(False)

        # فعال/غیرفعال
        self.refer_date.setEnabled(not disable_all)
        self.invest_box.setEnabled(False)
        self.expert_order_date.setEnabled(False)
        self.verdict_date.setEnabled(False)
        self.objection_deadline.setEnabled(False)
        self.obj_box.setEnabled(False)
        self.objection_date.setEnabled(False)
        self.verdict_box.setEnabled(False)

    # ---------- Signals Logic ----------
    def _on_refer_date_changed(self, _):
        # هر بار تاریخ جلسه تغییر کند، انتخاب تحقیق/کارشناسی و وابسته‌ها ریست شوند
        self.invest_yes.setChecked(False)
        self.invest_no.setChecked(False)
        self.expert_order_date.clear()
        self.expert_order_date.setEnabled(False)
        self.verdict_date.clear()
        self.verdict_date.setEnabled(False)
        self.objection_deadline.clear()
        self.objection_deadline.setEnabled(False)
        self.obj_yes.setChecked(False)
        self.obj_no.setChecked(False)
        self.obj_box.setEnabled(False)
        self.objection_date.clear()
        self.objection_date.setEnabled(False)
        self.v_approve.setChecked(False)
        self.v_adjust.setChecked(False)
        self.verdict_box.setEnabled(False)

        txt = self.refer_date.text().strip()
        if not _valid_jalali(txt):
            self.invest_box.setEnabled(False)
            return
        today = jdatetime.date.today()
        try:
            in_date = jdatetime.datetime.strptime(txt, "%Y/%m/%d").date()
            # جلسه آینده: فعلاً فقط تاریخ جلسه کافی است؛ جلسه گذشته/امروز: باید تحقیق/کارشناسی تعیین شود
            self.invest_box.setEnabled(in_date <= today)
        except Exception:
            self.invest_box.setEnabled(False)

    def _on_invest_changed(self):
        if self.invest_yes.isChecked():
            self.expert_order_date.setEnabled(True)
            self.verdict_date.setEnabled(True)
            self.objection_deadline.clear()
            self.objection_deadline.setEnabled(False)
            self.obj_box.setEnabled(False)
            self.objection_date.setEnabled(False)
            self.objection_date.clear()
            self.verdict_box.setEnabled(False)
        elif self.invest_no.isChecked():
            self.expert_order_date.clear()
            self.expert_order_date.setEnabled(False)
            self.verdict_date.setEnabled(True)
            self.objection_deadline.clear()
            self.objection_deadline.setEnabled(False)
            self.obj_box.setEnabled(False)
            self.objection_date.setEnabled(False)
            self.objection_date.clear()
            self.verdict_box.setEnabled(False)

    def _on_verdict_date_changed(self, _):
        txt = self.verdict_date.text().strip()
        if not _valid_jalali(txt):
            self.objection_deadline.clear()
            self.obj_box.setEnabled(False)
            self.verdict_box.setEnabled(False)
            self.objection_date.clear()
            self.objection_date.setEnabled(False)
            return
        try:
            vd = jdatetime.datetime.strptime(txt, "%Y/%m/%d")
            deadline = vd + jdatetime.timedelta(days=20)
            self.objection_deadline.setText(deadline.strftime("%Y/%m/%d"))
            self.objection_deadline.setEnabled(True)
            today = jdatetime.date.today()
            if deadline.date() <= today:
                # مهلت گذشته → باید اعتراض/رأی مشخص شوند
                self.obj_box.setEnabled(True)
                self.verdict_box.setEnabled(True)
            else:
                # مهلت نگذشته → اعتراض/رأی نباید فعال باشند
                self.obj_box.setEnabled(False)
                self.objection_date.clear()
                self.objection_date.setEnabled(False)
                self.verdict_box.setEnabled(False)
        except Exception:
            self.objection_deadline.clear()
            self.obj_box.setEnabled(False)
            self.verdict_box.setEnabled(False)
            self.objection_date.clear()
            self.objection_date.setEnabled(False)

    def _on_obj_changed(self):
        if self.obj_yes.isChecked():
            self.objection_date.setEnabled(True)
        else:
            self.objection_date.setEnabled(False)
            self.objection_date.clear()

    def validate_and_collect(self, today_j: jdatetime.date):
        """
        خروجی:
        data: dict | None
        need_finalize: bool
        need_reminder: bool
        dlg_status: str
        err: str | None

        تحقیق = بله (طبق سناریو):
        - اگر رأی نداده → بدون هشدار، فرم یادآوری بعدی باز شود (Status: پیگیری پرونده بدوی)
        - اگر رأی داده:
            * اگر مهلت اعتراض 20روزه نگذشته → بدون دیالوگ ذخیره (status=مهلت اعتراض, last_action_date=رأی+20)
            * اگر مهلت گذشته:
                    1) باید «اعتراض شده؟» انتخاب شود (وگرنه err="obj-missing")
                    2) باید «رأی بدوی» انتخاب شود (وگرنه err="verdict-result-missing")
                    3) اعتراض=خیر → need_finalize=True (دیالوگ مختومه در MainWindow)
                    اعتراض=بله → تاریخ اعتراض لازم (وگرنه err="obj-date-missing") و ذخیره با status=اعتراض به رأی
        نکته: تاریخ صدور قرار کارشناسی اختیاری است.
        """
        fmt = "%Y/%m/%d"

        # 0) تاریخ جلسه هیأت بدوی
        r = self.refer_date.text().strip()
        if not _valid_jalali(r):
            # خالی/نامعتبر → لایه‌ی بالا Reminder می‌گیرد (جلسه اول)
            return None, False, True, "جلسه اول هیأت بدوی", "empty"

        r_date = jdatetime.datetime.strptime(r, fmt).date()
        if r_date > today_j:
            # جلسه در آینده → همان تاریخ جلسه آخرین اقدام
            data = {
                'result': "ارجاع به هیأت بدوی",
                'refer_date': r,
                'last_action_date': r,
                'needs_investigation': '',
                'expert_order_date': '',
                'verdict_date': '',
                'objection_deadline': '',
                'objection_done': '',
                'objection_date': '',
                'verdict_result': '',
                'reminder_notes': [],
                'status': 'جلسه اول هیأت بدوی'
            }
            return data, False, False, "", None

        # 1) جلسه امروز/گذشته → باید تحقیق مشخص شود
        if not (self.invest_yes.isChecked() or self.invest_no.isChecked()):
            return None, False, False, "", "invest-missing"

        # کمک‌تابع: منطق مشترک وقتی تاریخ رأی داریم (برای تحقیق=بله/خیر یکسان)
        def _process_verdict_path(vd_txt: str, needs_invest_txt: str):
            vd_dt = jdatetime.datetime.strptime(vd_txt, fmt)
            deadline = (vd_dt + jdatetime.timedelta(days=20)).date()

            # مهلت اعتراض نگذشته
            if deadline > today_j:
                data = {
                    'result': "ارجاع به هیأت بدوی",
                    'refer_date': r,
                    'needs_investigation': needs_invest_txt,
                    'expert_order_date': self.expert_order_date.text().strip() if self.invest_yes.isChecked() else '',
                    'verdict_date': vd_txt,
                    'objection_deadline': deadline.strftime(fmt),
                    'objection_done': '',
                    'objection_date': '',
                    'verdict_result': '',
                    'reminder_notes': [],
                    'last_action_date': deadline.strftime(fmt),
                    'status': 'مهلت اعتراض'
                }
                return data, False, False, "", None

            # مهلت اعتراض گذشته → باید اعتراض/رأی مشخص شود
            if not (self.obj_yes.isChecked() or self.obj_no.isChecked()):
                return None, False, False, "", "obj-missing"

            verdict_result = ""
            if self.v_approve.isChecked():
                verdict_result = "تایید"
            elif self.v_adjust.isChecked():
                verdict_result = "تعدیل"
            if not verdict_result:
                return None, False, False, "", "verdict-result-missing"

            if self.obj_no.isChecked():
                # اعتراض نشده → مختومه (MainWindow دیالوگ مختومه را باز می‌کند)
                data = {
                    'result': "ارجاع به هیأت بدوی",
                    'refer_date': r,
                    'needs_investigation': needs_invest_txt,
                    'expert_order_date': self.expert_order_date.text().strip() if self.invest_yes.isChecked() else '',
                    'verdict_date': vd_txt,
                    'objection_deadline': (vd_dt + jdatetime.timedelta(days=20)).strftime(fmt),
                    'objection_done': 'خیر',
                    'objection_date': '',
                    'verdict_result': verdict_result,
                    'reminder_notes': [],
                    'last_action_date': vd_txt,
                    'status': 'مختومه'
                }
                return data, True, False, "", None

            # اعتراض شده → تاریخ اعتراض لازم است
            obj_date = self.objection_date.text().strip()
            if not _valid_jalali(obj_date):
                return None, False, False, "", "obj-date-missing"

            data = {
                'result': "ارجاع به هیأت بدوی",
                'refer_date': r,
                'needs_investigation': needs_invest_txt,
                'expert_order_date': self.expert_order_date.text().strip() if self.invest_yes.isChecked() else '',
                'verdict_date': vd_txt,
                'objection_deadline': (vd_dt + jdatetime.timedelta(days=20)).strftime(fmt),
                'objection_done': 'بله',
                'objection_date': obj_date,
                'verdict_result': verdict_result,
                'reminder_notes': [],
                'status': 'اعتراض به رأی'
            }
            return data, False, False, "", None

        # 2) شاخه تحقیق = خیر
        if self.invest_no.isChecked():
            vd = self.verdict_date.text().strip()
            if _valid_jalali(vd):
                return _process_verdict_path(vd, "خیر")
            # رأی ندارد → بدون هشدار، یادآوری پیگیری بدوی
            data = {
                'result': "ارجاع به هیأت بدوی",
                'refer_date': r,
                'needs_investigation': 'خیر',
                'expert_order_date': '',
                'verdict_date': '',
                'status': 'پیگیری پرونده بدوی'
            }
            return data, False, True, "پیگیری پرونده بدوی", None

        # 3) شاخه تحقیق = بله
        vd = self.verdict_date.text().strip()

        # اگر تاریخ رأی نداد → بدون هشدار، یادآوری پیگیری بدوی باز شود
        if not _valid_jalali(vd):
            data = {
                'result': "ارجاع به هیأت بدوی",
                'refer_date': r,
                'needs_investigation': 'بله',
                'expert_order_date': self.expert_order_date.text().strip(),  # اختیاری
                'verdict_date': '',
                'status': 'پیگیری پرونده بدوی'
            }
            return data, False, True, "پیگیری پرونده بدوی", None

        # اگر تاریخ رأی داد → همان منطق مسیر «خیر»
        return _process_verdict_path(vd, "بله")