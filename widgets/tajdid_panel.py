# widgets/tajdid_panel.py
# -*- coding: utf-8 -*-
import jdatetime
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QGroupBox, QHBoxLayout, QRadioButton,
    QButtonGroup, QLabel, QCheckBox, QComboBox
)
from PySide6.QtCore import Qt

def _valid_jalali(s: str) -> bool:
    try:
        jdatetime.datetime.strptime(s.strip(), "%Y/%m/%d")
        return True
    except Exception:
        return False

def _jplus(date_text: str, days: int) -> str:
    d = jdatetime.datetime.strptime(date_text.strip(), "%Y/%m/%d")
    return (d + jdatetime.timedelta(days=days)).strftime("%Y/%m/%d")

class TajdidPanel(QWidget):
    """
    پنل هیأت تجدیدنظر — منطق تا جای ممکن همسان با BodaviPanel
    (تفاوت طبیعی: مهلت 251 = 30 روز به‌جای 20 روز).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # برای سازگاری با QSS عباسپور
        self.setLayoutDirection(Qt.RightToLeft)
        self.setProperty("rtl", "true")
        self._build_ui()

    
        
# --- Aliases & hidden bridge widgets for MainWindow compatibility ---
        try:
            # simple field aliases
            self.verdict_date = self.verdict_date_tajdid
            self.objection_deadline = self.deadline_251
            self.objection_date = self.obj251_date
            self.obj_yes = self.obj251_yes
            self.obj_no = self.obj251_no

            # hidden 'verdict' text reflecting vr_* radios
            from PySide6.QtWidgets import QLineEdit, QCheckBox, QComboBox
            self.verdict = QLineEdit()
            self.verdict.setVisible(False)

            def _sync_verdict_from_radios():
                if self.vr_taeid.isChecked():
                    self.verdict.setText("تأیید")
                elif self.vr_tadil.isChecked():
                    self.verdict.setText("تعدیل")
                else:
                    self.verdict.clear()

            def _sync_verdict_to_radios(txt):
                t = (txt or "").strip()
                self.vr_taeid.setChecked(t in ("تایید","تأیید"))
                self.vr_tadil.setChecked(t == "تعدیل")

            self.vr_taeid.toggled.connect(_sync_verdict_from_radios)
            self.vr_tadil.toggled.connect(_sync_verdict_from_radios)
            self.verdict.textChanged.connect(_sync_verdict_to_radios)

            # hidden checkbox for needs_investigation_tajdid (maps to inv_yes/no)
            self.needs_investigation = QCheckBox()
            self.needs_investigation_tajdid = self.needs_investigation
            self.needs_investigation.setVisible(False)

            def _sync_need_from_checkbox(checked):
                self.inv_yes.setChecked(bool(checked))
                self.inv_no.setChecked(not bool(checked))

            def _sync_need_from_radios():
                self.needs_investigation.blockSignals(True)
                try:
                    self.needs_investigation.setChecked(self.inv_yes.isChecked())
                finally:
                    self.needs_investigation.blockSignals(False)

            self.needs_investigation.toggled.connect(_sync_need_from_checkbox)
            self.inv_yes.toggled.connect(_sync_need_from_radios)
            self.inv_no.toggled.connect(_sync_need_from_radios)

            # verdict_result combobox (hidden) used by Editor; keep it in sync with radios and 'verdict' text
            self.verdict_result = QComboBox(); self.verdict_result.setVisible(False)
            self.verdict_result.addItems(["", "تأیید", "تایید", "تعدیل", "نقض"])

            def _sync_combo_from_verdict(txt: str):
                items = [self.verdict_result.itemText(i) for i in range(self.verdict_result.count())]
                target = txt.strip() if txt and txt.strip() in items else ""
                self.verdict_result.blockSignals(True)
                try:
                    idx = self.verdict_result.findText(target)
                    self.verdict_result.setCurrentIndex(idx if idx >= 0 else 0)
                finally:
                    self.verdict_result.blockSignals(False)

            def _sync_verdict_from_combo(text: str):
                t = (text or "").strip()
                if t in ("تأیید","تایید"):
                    self.vr_taeid.setChecked(True); self.vr_tadil.setChecked(False); self.verdict.setText("تأیید")
                elif t == "تعدیل":
                    self.vr_taeid.setChecked(False); self.vr_tadil.setChecked(True); self.verdict.setText("تعدیل")
                else:
                    self.vr_taeid.setChecked(False); self.vr_tadil.setChecked(False); self.verdict.clear()

            self.verdict.textChanged.connect(_sync_combo_from_verdict)
            self.verdict_result.currentTextChanged.connect(_sync_verdict_from_combo)

        except Exception:
            pass

    # ---------- UI ----------
    def _build_ui(self):
        form = QFormLayout(self)

        # قدم ۱: تاریخ جلسه هیأت تجدیدنظر
        self.refer_date = QLineEdit(); self.refer_date.setInputMask("0000/00/00;_")
        form.addRow("تاریخ جلسه هیأت تجدیدنظر:", self.refer_date)

        # قدم ۲: نیاز به تحقیق/کارشناسی؟
        self.invest_box = QGroupBox("نیاز به تحقیق و کارشناسی؟")
        self.invest_box.setLayoutDirection(Qt.RightToLeft)
        self.invest_box.setProperty("rtl", "true")
        h_inv = QHBoxLayout(self.invest_box)
        self.inv_yes = QRadioButton("بله")
        self.inv_no  = QRadioButton("خیر")
        self.inv_bg  = QButtonGroup(self)
        self.inv_bg.addButton(self.inv_yes, 1)
        self.inv_bg.addButton(self.inv_no, 0)
        h_inv.addWidget(self.inv_yes); h_inv.addWidget(self.inv_no)
        form.addRow(self.invest_box)

        # تاریخ قرار/ارجاع کارشناسی (اختیاری)
        self.expert_date = QLineEdit(); self.expert_date.setInputMask("0000/00/00;_")
        form.addRow("تاریخ قرار کارشناسی (اختیاری):", self.expert_date)

        # قدم ۳: تاریخ رأی تجدیدنظر
        self.verdict_date_tajdid = QLineEdit(); self.verdict_date_tajdid.setInputMask("0000/00/00;_")
        form.addRow("تاریخ رأی هیأت تجدیدنظر:", self.verdict_date_tajdid)

        # مهلت درخواست ۲۵۱ (۳۰روزه) — فقط خواندنی
        self.deadline_251 = QLineEdit(); self.deadline_251.setReadOnly(True)
        form.addRow("مهلت درخواست ۲۵۱:", self.deadline_251)

        # درخواست ۲۵۱؟
        self.obj251_box = QGroupBox("درخواست تجدید رسیدگی ماده ۲۵۱ انجام شده؟")
        self.obj251_box.setLayoutDirection(Qt.RightToLeft)
        self.obj251_box.setProperty("rtl", "true")
        h251 = QHBoxLayout(self.obj251_box)
        self.obj251_yes = QRadioButton("بله")
        self.obj251_no  = QRadioButton("خیر")
        self.obj251_bg  = QButtonGroup(self)
        self.obj251_bg.addButton(self.obj251_yes, 1)
        self.obj251_bg.addButton(self.obj251_no, 0)
        h251.addWidget(self.obj251_yes); h251.addWidget(self.obj251_no)
        form.addRow(self.obj251_box)

        # تاریخ ثبت درخواست ۲۵۱
        self.obj251_date = QLineEdit(); self.obj251_date.setInputMask("0000/00/00;_")
        form.addRow("تاریخ ثبت درخواست ۲۵۱:", self.obj251_date)

        # نتیجه رأی تجدیدنظر
        self.vr_box = QGroupBox("نتیجه رأی تجدیدنظر:")
        self.vr_box.setLayoutDirection(Qt.RightToLeft)
        self.vr_box.setProperty("rtl", "true")
        h_vr = QHBoxLayout(self.vr_box)
        self.vr_taeid = QRadioButton("تأیید")
        self.vr_tadil = QRadioButton("تعدیل")
        self.vr_bg    = QButtonGroup(self)
        for rb in (self.vr_taeid, self.vr_tadil):
            self.vr_bg.addButton(rb)
        h_vr.addWidget(self.vr_taeid); h_vr.addWidget(self.vr_tadil)
        form.addRow(self.vr_box)

        # احراز دبیرخانه شورا
        self.ver_box = QGroupBox("احراز دبیرخانه شورا:")
        self.ver_box.setLayoutDirection(Qt.RightToLeft)
        self.ver_box.setProperty("rtl", "true")
        h_ver = QHBoxLayout(self.ver_box)
        self.ver_yes = QRadioButton("بله")
        self.ver_no  = QRadioButton("خیر")
        self.ver_bg  = QButtonGroup(self)
        self.ver_bg.addButton(self.ver_yes, 1)
        self.ver_bg.addButton(self.ver_no, 0)
        h_ver.addWidget(self.ver_yes); h_ver.addWidget(self.ver_no)
        form.addRow(self.ver_box)

        # تاریخ جلسه شورا
        self.council_date = QLineEdit(); self.council_date.setInputMask("0000/00/00;_")
        form.addRow("تاریخ جلسه شورا:", self.council_date)

        # اتصالات سیگنال‌ها
        self.refer_date.textChanged.connect(self._on_refer_date_changed)
        self.inv_bg.buttonClicked.connect(lambda _: self._on_invest_changed())
        self.verdict_date_tajdid.textChanged.connect(self._on_verdict_date_changed)
        self.obj251_bg.buttonClicked.connect(lambda _: self._on_obj251_changed())
        self.ver_bg.buttonClicked.connect(lambda _: self._on_ver_changed())

        # چیدمان
        form.setLabelAlignment(Qt.AlignRight)

        # حالت اولیه
        self.reset(disable_all=True)

    # ---------- States ----------
    def start(self):
        """وقتی از MainWindow فعال شد، فقط تاریخ جلسه باز باشد."""
        self.reset(disable_all=False)

    def reset(self, disable_all: bool = True):
        # پاک‌سازی انتخاب‌ها/متن‌ها
        for w in (self.refer_date, self.expert_date, self.verdict_date_tajdid,
                  self.deadline_251, self.obj251_date, self.council_date):
            w.clear()

        for bg in (self.inv_bg, self.vr_bg, self.obj251_bg, self.ver_bg):
            bg.setExclusive(False)
            for b in bg.buttons():
                b.setChecked(False)
            bg.setExclusive(True)

        # فعال/غیرفعال همسان با بدوی
        self.refer_date.setEnabled(not disable_all)

        self.invest_box.setEnabled(False)
        self.expert_date.setEnabled(False)
        self.verdict_date_tajdid.setEnabled(False)
        self.deadline_251.setEnabled(False)

        self.obj251_box.setEnabled(False)
        self.obj251_date.setEnabled(False)

        self.vr_box.setEnabled(False)
        self.ver_box.setEnabled(False)
        self.council_date.setEnabled(False)

    # ---------- Signals Logic (mirroring BodaviPanel) ----------
    def _on_refer_date_changed(self, _):
        # هر تغییر تاریخ جلسه → ریست آبشاری
        self.inv_yes.setChecked(False); self.inv_no.setChecked(False)
        self.invest_box.setEnabled(False)

        self.expert_date.clear(); self.expert_date.setEnabled(False)

        self.verdict_date_tajdid.clear(); self.verdict_date_tajdid.setEnabled(False)
        self.deadline_251.clear(); self.deadline_251.setEnabled(False)

        self.obj251_yes.setChecked(False); self.obj251_no.setChecked(False)
        self.obj251_box.setEnabled(False)
        self.obj251_date.clear(); self.obj251_date.setEnabled(False)

        for rb in (self.vr_taeid, self.vr_tadil):
            rb.setChecked(False)
        self.vr_box.setEnabled(False)

        self.ver_yes.setChecked(False); self.ver_no.setChecked(False)
        self.ver_box.setEnabled(False)
        self.council_date.clear(); self.council_date.setEnabled(False)

        txt = self.refer_date.text().strip()
        if not _valid_jalali(txt):
            return
        try:
            in_date = jdatetime.datetime.strptime(txt, "%Y/%m/%d").date()
            today = jdatetime.date.today()
            # جلسه آینده: فعلاً فقط تاریخ جلسه کافی است؛ جلسه امروز/گذشته: اجازه‌ی انتخاب تحقیق
            self.invest_box.setEnabled(in_date <= today)
        except Exception:
            self.invest_box.setEnabled(False)

    def _on_invest_changed(self):
        if self.inv_yes.isChecked():
            self.expert_date.setEnabled(True)
            self.verdict_date_tajdid.setEnabled(True)
            self.deadline_251.clear(); self.deadline_251.setEnabled(False)
            self.obj251_box.setEnabled(False)
            self.obj251_date.clear(); self.obj251_date.setEnabled(False)
            self.vr_box.setEnabled(False)
            self.ver_box.setEnabled(False); self.council_date.setEnabled(False); self.council_date.clear()
        elif self.inv_no.isChecked():
            self.expert_date.clear(); self.expert_date.setEnabled(False)
            self.verdict_date_tajdid.setEnabled(True)
            self.deadline_251.clear(); self.deadline_251.setEnabled(False)
            self.obj251_box.setEnabled(False)
            self.obj251_date.clear(); self.obj251_date.setEnabled(False)
            self.vr_box.setEnabled(False)
            self.ver_box.setEnabled(False); self.council_date.setEnabled(False); self.council_date.clear()

    def _on_verdict_date_changed(self, _):
        txt = self.verdict_date_tajdid.text().strip()
        if not _valid_jalali(txt):
            self.deadline_251.clear(); self.deadline_251.setEnabled(False)
            self.obj251_box.setEnabled(False); self.obj251_yes.setChecked(False); self.obj251_no.setChecked(False)
            self.obj251_date.clear(); self.obj251_date.setEnabled(False)
            self.vr_box.setEnabled(False)
            # ⬇️ احراز همیشه خاموش تا وقتی ۲۵۱=بله شود
            self.ver_box.setEnabled(False); self.ver_yes.setChecked(False); self.ver_no.setChecked(False)
            self.council_date.clear(); self.council_date.setEnabled(False)
            return
        try:
            vd = jdatetime.datetime.strptime(txt, "%Y/%m/%d")
            deadline = vd + jdatetime.timedelta(days=30)
            self.deadline_251.setText(deadline.strftime("%Y/%m/%d"))
            self.deadline_251.setEnabled(True)

            today = jdatetime.date.today()
            if deadline.date() <= today:
                # مهلت ۳۰روزه گذشته → فقط ۲۵۱ و «نتیجه رأی» فعال شوند
                self.obj251_box.setEnabled(True)
                self.vr_box.setEnabled(True)
                # ⬇️ احراز هنوز خاموش بماند؛ فقط وقتی ۲۵۱=بله شد، روشنش می‌کنیم
                self.ver_box.setEnabled(False); self.ver_yes.setChecked(False); self.ver_no.setChecked(False)
                self.council_date.clear(); self.council_date.setEnabled(False)
            else:
                # هنوز مهلت داریم → هیچ‌کدام از این‌ها فعال نیستند
                self.obj251_box.setEnabled(False)
                self.obj251_date.clear(); self.obj251_date.setEnabled(False)
                self.obj251_yes.setChecked(False); self.obj251_no.setChecked(False)
                self.vr_box.setEnabled(False)
                self.ver_box.setEnabled(False); self.ver_yes.setChecked(False); self.ver_no.setChecked(False)
                self.council_date.clear(); self.council_date.setEnabled(False)
        except Exception:
            self.deadline_251.clear(); self.deadline_251.setEnabled(False)
            self.obj251_box.setEnabled(False); self.vr_box.setEnabled(False)
            self.obj251_date.clear(); self.obj251_date.setEnabled(False)
            self.ver_box.setEnabled(False); self.council_date.clear(); self.council_date.setEnabled(False)

    def _on_obj251_changed(self):
        if self.obj251_yes.isChecked():
            self.obj251_date.setEnabled(True)
            # ⬇️ فقط وقتی ۲۵۱=بله → احراز فعال شود
            self.ver_box.setEnabled(True)
        else:
            self.obj251_date.setEnabled(False); self.obj251_date.clear()
            # ⬇️ اگر ۲۵۱=خیر یا نامشخص → احراز غیرفعال/پاک‌سازی شود
            self.ver_box.setEnabled(False)
            self.ver_yes.setChecked(False); self.ver_no.setChecked(False)
            self.council_date.setEnabled(False); self.council_date.clear()

    def _on_ver_changed(self):
        # احراز=بله → امکان ثبت تاریخ جلسه شورا
        self.council_date.setEnabled(self.ver_yes.isChecked())

    # ---------- Validate ----------
    def validate_and_collect(self, today_j: jdatetime.date):
        """
        خروجی:
          data: dict | None
          finalize: bool
          reminder: bool
          status: str
          err: یکی از {None,"none","invest-missing","verdict-missing","obj-missing","verdict-result-missing","obj-date-missing","verify-missing"}
        """
        fmt = "%Y/%m/%d"
        data = {}

        # ── قدم ۱: تاریخ جلسه ──
        rtxt = self.refer_date.text().strip()
        if not _valid_jalali(rtxt):
            # مثل بدوی: خالی/نامعتبر → یادآور جلسه اول
            return None, False, True, "جلسه اول هیأت تجدید نظر", "none"

        rj = jdatetime.datetime.strptime(rtxt, fmt).date()
        if rj > today_j:
            # جلسه آینده → ذخیرهٔ ساده
            data = {
                'tajdid_refer_date': rtxt,
                'needs_investigation_tajdid': '',
                'tajdid_expert_date': '',
                'verdict_date_tajdid': '',
                'objection_deadline_tajdid': '',
                'objection_done_tajdid': '',
                'objection_date_tajdid': '',
                'verdict_result_tajdid': '',
                'last_action_date': rtxt,
                'status': 'جلسه اول هیأت تجدید نظر'
            }
            return data, False, False, "جلسه اول هیأت تجدید نظر", None

        # ── قدم ۲: تحقیق/کارشناسی الزامی ──
        if not (self.inv_yes.isChecked() or self.inv_no.isChecked()):
            return None, False, False, "", "invest-missing"

        # کمک‌تابع: مسیر مشترک وقتی رأی داریم (آینه‌ی بدوی؛ با مهلت ۳۰روزه)
        def _process_verdict_path(vd_txt: str, needs_invest_txt: str):
            vd_dt = jdatetime.datetime.strptime(vd_txt, fmt)
            deadline = (vd_dt + jdatetime.timedelta(days=30)).date()

            # مهلت ۳۰روزه هنوز نگذشته
            if deadline > today_j:
                d = {
                    'tajdid_refer_date': rtxt,
                    'needs_investigation_tajdid': needs_invest_txt,
                    'tajdid_expert_date': self.expert_date.text().strip() if self.inv_yes.isChecked() else '',
                    'verdict_date_tajdid': vd_txt,
                    'objection_deadline_tajdid': deadline.strftime(fmt),
                    'objection_done_tajdid': '',
                    'objection_date_tajdid': '',
                    'verdict_result_tajdid': '',
                    'last_action_date': deadline.strftime(fmt),
                    'status': 'مهلت درخواست ۲۵۱'
                }
                return d, False, False, "مهلت درخواست ۲۵۱", None

            # مهلت گذشته → باید ۲۵۱؟ و نتیجه رأی مشخص شود
            if not (self.obj251_yes.isChecked() or self.obj251_no.isChecked()):
                return None, False, False, "", "obj-missing"

            verdict_result = ""
            if self.vr_taeid.isChecked(): verdict_result = "تأیید"
            elif self.vr_tadil.isChecked(): verdict_result = "تعدیل"
            if not verdict_result:
                return None, False, False, "", "verdict-result-missing"

            if self.obj251_no.isChecked():
                # ۲۵۱ نشده → مختومه (عین بدوی)
                d = {
                    'tajdid_refer_date': rtxt,
                    'needs_investigation_tajdid': needs_invest_txt,
                    'tajdid_expert_date': self.expert_date.text().strip() if self.inv_yes.isChecked() else '',
                    'verdict_date_tajdid': vd_txt,
                    'objection_deadline_tajdid': (vd_dt + jdatetime.timedelta(days=30)).strftime(fmt),
                    'objection_done_tajdid': 'خیر',
                    'objection_date_tajdid': '',
                    'verdict_result_tajdid': verdict_result,
                    'last_action_date': vd_txt,
                    'status': 'مختومه'
                }
                return d, True, False, "", None

            # ۲۵۱ شده → تاریخ ثبت ۲۵۱ لازم
            obj_date = self.obj251_date.text().strip()
            if not _valid_jalali(obj_date):
                return None, False, False, "", "obj-date-missing"

            d = {
                'tajdid_refer_date': rtxt,
                'needs_investigation_tajdid': needs_invest_txt,
                'tajdid_expert_date': self.expert_date.text().strip() if self.inv_yes.isChecked() else '',
                'verdict_date_tajdid': vd_txt,
                'objection_deadline_tajdid': (vd_dt + jdatetime.timedelta(days=30)).strftime(fmt),
                'objection_done_tajdid': 'بله',
                'objection_date_tajdid': obj_date,
                'verdict_result_tajdid': verdict_result
            }
            # از این نقطه به بعد — منطق اختصاصی احراز/شورا (مثل کد قبلی خودت)
            return d, False, False, "", None

        # ── شاخه تحقیق = خیر ──
        if self.inv_no.isChecked():
            vd = self.verdict_date_tajdid.text().strip()
            if _valid_jalali(vd):
                base_data, need_fin, need_rem, st, err = _process_verdict_path(vd, "خیر")
                if err or need_fin or need_rem:
                    return base_data, need_fin, need_rem, st, err
                # --- ادامهٔ منطق اختصاصی بعد از «تاریخ ثبت ۲۵۱» ---
                # احراز دبیرخانه شورا بعد از ۲۵۱
                self.ver_box.setEnabled(True)
                ver_id = self.ver_bg.checkedId()
                if ver_id < 0:
                    ver_id = -1  # اختیاری شد؛ عدم انتخاب یعنی بدون ست‌کردن وضعیت احراز
                if ver_id == 0:
                    base_data['verification_status'] = "خیر"
                    # منطق قبلی (مختومه/مبلغ نهایی) را به سطح MainWindow واگذار یا غیرفعال کن
                    return base_data, False, False, "", None
                if ver_id == 1:
                    base_data['verification_status'] = "بله"
                self.council_date.setEnabled(True)
                ctxt = self.council_date.text().strip()
                if not ctxt:
                    # اختیاری: اگر تاریخ شورا خالی بود، یادآوری را تحمیل نکن
                    return base_data, False, False, "", None
                if _valid_jalali(ctxt):
                    base_data['council_date'] = ctxt
                    cj = jdatetime.datetime.strptime(ctxt, fmt).date()
                    if cj >= today_j:
                        base_data['last_action_date'] = ctxt
                        base_data['status'] = "جلسه شورا"
                return base_data, False, False, "", None
            # تاریخ رأی نامشخص → مثل بدوی، ولی ذخیرهٔ حداقلی انجام بده و Reminder بگذار
            data = {
                'tajdid_refer_date': rtxt,
                'needs_investigation_tajdid': 'خیر',
                'tajdid_expert_date': '',
                'verdict_date_tajdid': '',
                'objection_deadline_tajdid': '',
                'objection_done_tajdid': '',
                'objection_date_tajdid': '',
                'verdict_result_tajdid': '',
                'last_action_date': rtxt,
                'status': 'پیگیری پرونده تجدیدنظر'
            }
            return data, False, True, 'پیگیری پرونده تجدیدنظر', None
        # ── شاخه تحقیق = بله ──
        vd = self.verdict_date_tajdid.text().strip()
        if not _valid_jalali(vd):
            # رأی نامشخص → ذخیرهٔ حداقلی + Reminder (همسو با بدوی)
            _expert = (self.expert_date.text().strip() or '')
            if not _valid_jalali(_expert):
                _expert = ''
            data = {
                'tajdid_refer_date': rtxt,
                'needs_investigation_tajdid': 'بله',
                'tajdid_expert_date': _expert,
                'verdict_date_tajdid': '',
                'objection_deadline_tajdid': '',
                'objection_done_tajdid': '',
                'objection_date_tajdid': '',
                'verdict_result_tajdid': '',
                'last_action_date': rtxt,
                'status': 'پیگیری پرونده تجدیدنظر'
            }
            return data, False, True, 'پیگیری پرونده تجدیدنظر', None

        # رأی دارد → همان منطق مشترک
        base_data, need_fin, need_rem, st, err = _process_verdict_path(vd, "بله")
        if err or need_fin or need_rem:
            return base_data, need_fin, need_rem, st, err

        # --- ادامهٔ منطق اختصاصی بعد از «تاریخ ثبت ۲۵۱» ---
        # احراز دبیرخانه شورا بعد از ۲۵۱
        self.ver_box.setEnabled(True)
        ver_id = self.ver_bg.checkedId()
        if ver_id < 0:
            ver_id = -1  # اختیاری شد؛ عدم انتخاب یعنی بدون ست‌کردن وضعیت احراز
        if ver_id == 0:
            base_data['verification_status'] = "خیر"
            # منطق قبلی (مختومه/مبلغ نهایی) را به سطح MainWindow واگذار یا غیرفعال کن
            return base_data, False, False, "", None

        if ver_id == 1:
            base_data['verification_status'] = "بله"
        self.council_date.setEnabled(True)
        ctxt = self.council_date.text().strip()
        if not ctxt:
            # اختیاری: اگر تاریخ شورا خالی بود، یادآوری را تحمیل نکن
            return base_data, False, False, "", None
        if _valid_jalali(ctxt):
            base_data['council_date'] = ctxt
            cj = jdatetime.datetime.strptime(ctxt, fmt).date()
            if cj >= today_j:
                base_data['last_action_date'] = ctxt
                base_data['status'] = "جلسه شورا"
        return base_data, False, False, "", None