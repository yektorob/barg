#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from contextlib import suppress
import os

_YES = {"TRUE","True","true","1","بله","Yes","YES","y","Y"}
_NO  = {"FALSE","False","false","0","خیر","No","NO","n","N"}

def _truthy(val: str) -> bool:
    return str(val or "").strip() in _YES

def _falsy(val: str) -> bool:
    return str(val or "").strip() in _NO
def _set_amount_lineedit(editor, widget, raw_value):
    """
    مقدار عددی رو با کاما (هزارگان) تو QLineEdit می‌نویسه.
    اگر مقدار خالی بود، فقط پاک می‌کند.
    """
    if not hasattr(widget, "setText"):
        return

    txt = str(raw_value or "").strip()
    if not txt:
        widget.clear()
        return

    # نرمال‌سازی: حذف کاما، تبدیل به int، بعد فرمت دوباره
    try:
        normalized = str(int(txt.replace(",", "")))
        try:
            # اگر ادیتور متد فرمت خودش رو دارد، از همون استفاده کن
            if hasattr(editor, "_format_with_commas"):
                normalized = editor._format_with_commas(normalized)
            else:
                normalized = "{:,}".format(int(normalized))
        except Exception:
            pass
        widget.setText(normalized)
    except Exception:
        # اگر هر مشکلی بود، حداقل خام نوشتنش
        widget.setText(txt)
def prefill_editor_window(editor, r: dict):
    """
    تمام پرکردن فیلدهای EditorWindow از روی رکورد «r» را انجام می‌دهد.
    این تابع به‌صورت امن از متدهای داخلی خود EditorWindow برای به‌روزرسانی UI استفاده می‌کند.
    """
    # ================== پایه (فرم اصلی) ==================
    editor.archive.setText(str(r.get('archive', '')).strip())
    editor.national_id.setText(str(r.get('national_id', '')).strip())
    editor.company.setText(str(r.get('company_name', '')).strip())
    editor.fiscal.setText(str(r.get('fiscal_year', '')).strip())
    editor.entry.setText(str(r.get('entry_date', '')).strip())

    case_raw = str(r.get('case_type', '')).strip()

    # اگر نسخهٔ جدید با چک‌باکس‌ها باشد
    if hasattr(editor, "case_checkboxes"):
        # نرمال‌سازی جداکننده‌ها: «،» فارسی → کاما
        norm = case_raw.replace("،", ",")
        parts = [p.strip() for p in norm.split(",") if p.strip()]

        selected = set(parts)

        # ست‌کردن چندتایی چک‌باکس‌ها
        for cb in editor.case_checkboxes:
            cb.setChecked(cb.text().strip() in selected)
    else:
        # برای سازگاری قدیمی، اگر هنوز group_case رادیویی بود
        editor._set_radio_by_text(editor.group_case, case_raw)
    editor.submit_date.setText(str(r.get('submit_date', '')).strip())
    try:
        dd = int(r.get('deadline_days', 0))
    except Exception:
        dd = 0
    editor.deadline_days.setValue(dd)
    editor._update_due()
    if str(r.get('due_date', '')).strip():
        editor.due_date.setText(str(r.get('due_date', '')).strip())

    editor._set_radio_by_text(editor.group_status, str(r.get('submit_status', '')).strip())
    editor._on_status_changed(editor.group_status.checkedId())
    editor.upload_date.setText(str(r.get('upload_date', '')).strip())

    # فایل‌های اپلود شده
    with suppress(Exception):
        editor.upload_list.clear()
        editor.uploaded_files = editor._coerce_uploaded(r.get('uploaded_files'))
        for p in editor.uploaded_files:
            editor.upload_list.addItem(os.path.basename(p))

    # ارزیابی
    val_has_ass = str(r.get('has_assessment', '')).strip()
    if val_has_ass:
        editor._set_radio_by_text(editor.group_has_ass, "بله" if _truthy(val_has_ass) else "خیر")
    editor._on_assessment_changed(editor.group_has_ass.checkedId())
    editor.assess_date.setText(str(r.get('assessment_date', '')).strip())
    editor._update_assess_deadline()
    if str(r.get('assessment_deadline', '')).strip():
        editor.assess_deadline.setText(str(r.get('assessment_deadline', '')).strip())

    # مبلغ مالیات کلی (jarime_amount)
    with suppress(Exception):
        if hasattr(editor, "penalty_amount"):
            _set_amount_lineedit(editor, editor.penalty_amount, r.get('jarime_amount', ''))

    # جریمه مخصوص «مالیات بر عملکرد»
    with suppress(Exception):
        if hasattr(editor, "performance_penalty"):
            _set_amount_lineedit(editor, editor.performance_penalty, r.get('performance_penalty', ''))

    # دوره‌های ارزش افزوده: vat_p1_tax / vat_p1_penalty / ... / vat_p4_*
    with suppress(Exception):
        if hasattr(editor, "vat_period_rows"):
            vat_tax_keys = [
                "vat_p1_tax",
                "vat_p2_tax",
                "vat_p3_tax",
                "vat_p4_tax",
            ]
            vat_penalty_keys = [
                "vat_p1_penalty",
                "vat_p2_penalty",
                "vat_p3_penalty",
                "vat_p4_penalty",
            ]
            for (row_w, tax_edit, pen_edit), k_tax, k_pen in zip(
                editor.vat_period_rows, vat_tax_keys, vat_penalty_keys
            ):
                _set_amount_lineedit(editor, tax_edit, r.get(k_tax, ''))
                _set_amount_lineedit(editor, pen_edit, r.get(k_pen, ''))

    val_rep = str(r.get('report_exists', '')).strip()
    if val_rep:
        editor._set_radio_by_text(editor.group_report, val_rep)
    val_obj = str(r.get('objected', '')).strip()
    if val_obj:
        editor._set_radio_by_text(editor.group_objected, val_obj)
    editor._on_report_changed(editor.group_report.checkedId())
    editor._on_objected_changed(editor.group_objected.checkedId())

    editor.appeal_send.setText(str(r.get('appeal_send_date', '')).strip())
# فایل‌های گزارش رسیدگی
    with suppress(Exception):
        if hasattr(editor, "report_upload_list"):
            editor.report_upload_list.clear()
            editor.report_uploaded_files = editor._coerce_uploaded(
                r.get('report_uploaded_files')
            )
            for p in editor.report_uploaded_files:
                editor.report_upload_list.addItem(os.path.basename(p))

    with suppress(Exception):
        editor.petition_upload_list.clear()
        editor.petition_uploaded_files = editor._coerce_uploaded(r.get('petition_uploaded_files'))
        for p in editor.petition_uploaded_files:
            editor.petition_upload_list.addItem(os.path.basename(p))

    editor.mad238_entry_date.setText(str(r.get('mad238_entry_date', '')).strip())
    editor._update_mad238_agreement_deadline()
    if str(r.get('mad238_agreement_deadline', '')).strip():
        editor.mad238_agreement_deadline.setText(str(r.get('mad238_agreement_deadline', '')).strip())

    # یادداشت‌ها
    with suppress(Exception):
        if hasattr(editor.notes_w, "clear_all"):
            editor.notes_w.clear_all()
        notes = r.get('notes')
        if notes is None:
            notes = []
        if not isinstance(notes, list):
            notes = [notes]
        for t in notes:
            editor.notes_w.add_note(str(t))

    # ================== نتیجه ماده ۲۳۸ و سوئیچ پنل‌ها ==================
    try:
        res_txt = str(r.get('mad238_result', '') or r.get('agreement_result', '')).strip()
        editor._lock_bodavi_tajdid(disable=False)
        if res_txt == "تعدیل مالیات":
            editor.rb_adjust.setChecked(True)
        elif res_txt == "ارجاع به هیأت بدوی":
            editor.rb_refer.setChecked(True)
        editor._on_refer_toggled(editor.rb_refer.isChecked())
    except Exception:
        pass

    # ================== پنل بدوی ==================
    with suppress(Exception):
        if hasattr(editor.bodavi, "refer_date") and 'bodavi_session_date' in r:
            editor.bodavi.refer_date.setText(str(r.get('bodavi_session_date','')).strip())

        inv_txt = str(r.get('needs_investigation','')).strip()
        if hasattr(editor.bodavi, "invest_yes") and hasattr(editor.bodavi, "invest_no"):
            editor.bodavi.invest_yes.setAutoExclusive(False); editor.bodavi.invest_no.setAutoExclusive(False)
            if inv_txt in _YES:    editor.bodavi.invest_yes.setChecked(True);  editor.bodavi.invest_no.setChecked(False)
            elif inv_txt in _NO:   editor.bodavi.invest_yes.setChecked(False); editor.bodavi.invest_no.setChecked(True)
            else:                  editor.bodavi.invest_yes.setChecked(False); editor.bodavi.invest_no.setChecked(False)
            editor.bodavi.invest_yes.setAutoExclusive(True);  editor.bodavi.invest_no.setAutoExclusive(True)

        if hasattr(editor.bodavi, "expert_order_date"):
            editor.bodavi.expert_order_date.setText(str(r.get('expert_order_date','')).strip())

        if hasattr(editor.bodavi, "verdict_date"):
            editor.bodavi.verdict_date.setText(str(r.get('bodavi_verdict_date','')).strip())
        if hasattr(editor.bodavi, "objection_deadline"):
            editor.bodavi.objection_deadline.setText(str(r.get('bodavi_appeal_deadline','')).strip())

        val = str(r.get('bodavi_appeal_done','')).strip()
        if hasattr(editor.bodavi, "obj_yes") and hasattr(editor.bodavi, "obj_no"):
            editor.bodavi.obj_yes.setAutoExclusive(False); editor.bodavi.obj_no.setAutoExclusive(False)
            if val in _YES:        editor.bodavi.obj_yes.setChecked(True);  editor.bodavi.obj_no.setChecked(False)
            elif val in _NO:       editor.bodavi.obj_yes.setChecked(False); editor.bodavi.obj_no.setChecked(True)
            else:                  editor.bodavi.obj_yes.setChecked(False); editor.bodavi.obj_no.setChecked(False)
            editor.bodavi.obj_yes.setAutoExclusive(True);  editor.bodavi.obj_no.setAutoExclusive(True)

        if hasattr(editor.bodavi, "objection_date"):
            editor.bodavi.objection_date.setText(str(r.get('bodavi_appeal_date','')).strip())

        v_txt = str(r.get('bodavi_verdict','')).strip()
        if hasattr(editor.bodavi, "v_approve") and hasattr(editor.bodavi, "v_adjust"):
            editor.bodavi.v_approve.setAutoExclusive(False); editor.bodavi.v_adjust.setAutoExclusive(False)
            if v_txt == "تایید":   editor.bodavi.v_approve.setChecked(True); editor.bodavi.v_adjust.setChecked(False)
            elif v_txt == "تعدیل": editor.bodavi.v_approve.setChecked(False); editor.bodavi.v_adjust.setChecked(True)
            else:                  editor.bodavi.v_approve.setChecked(False); editor.bodavi.v_adjust.setChecked(False)
            editor.bodavi.v_approve.setAutoExclusive(True); editor.bodavi.v_adjust.setAutoExclusive(True)

    # ================== پنل تجدیدنظر (کامل، به ترتیب فرم) ==================
    with suppress(Exception):
        t = editor.tajdid

        # 1) نتیجه/مبلغ نهایی (در این فرم: QLineEdit به نام verdict)
        if hasattr(t, "verdict"):
            txt = str(r.get('final_amount', '') or r.get('verdict', '')).strip()
            t.verdict.setText(txt)

        # 2) نیاز به تحقیق و کارشناسی؟ (CheckBox + RadioGroup inv_yes/inv_no)
        need_inv = str(r.get('needs_investigation_tajdid','')).strip()
        if hasattr(t, "needs_investigation"):
            t.needs_investigation.setChecked(_truthy(need_inv))
        if hasattr(t, "inv_yes") and hasattr(t, "inv_no"):
            t.inv_yes.setAutoExclusive(False); t.inv_no.setAutoExclusive(False)
            if need_inv in _YES:   t.inv_yes.setChecked(True);  t.inv_no.setChecked(False)
            elif need_inv in _NO:  t.inv_yes.setChecked(False); t.inv_no.setChecked(True)
            else:                  t.inv_yes.setChecked(False); t.inv_no.setChecked(False)
            t.inv_yes.setAutoExclusive(True);  t.inv_no.setAutoExclusive(True)

        # 3) نتیجه رأی تجدیدنظر (RadioGroup: vr_taeid / vr_tadil) یا ComboBox verdict_result
        vr = str(r.get('verdict_result_tajdid','')).strip()
        if hasattr(t, "vr_taeid") and hasattr(t, "vr_tadil"):
            t.vr_taeid.setAutoExclusive(False); t.vr_tadil.setAutoExclusive(False)
            if vr in {"تایید","تأیید","تأیید"}: t.vr_taeid.setChecked(True); t.vr_tadil.setChecked(False)
            elif vr == "تعدیل":                 t.vr_taeid.setChecked(False); t.vr_tadil.setChecked(True)
            else:                               t.vr_taeid.setChecked(False); t.vr_tadil.setChecked(False)
            t.vr_taeid.setAutoExclusive(True);  t.vr_tadil.setAutoExclusive(True)
        if hasattr(t, "verdict_result") and hasattr(t.verdict_result, "findText"):
            try:
                idx = t.verdict_result.findText(vr)
                if idx >= 0: t.verdict_result.setCurrentIndex(idx)
            except Exception:
                pass

        # 4) تاریخ ارجاع/ثبت اولیه
        if hasattr(t, "refer_date"):
            t.refer_date.setText(str(r.get('tajdid_refer_date','')).strip())

        # 5) تاریخ قرار کارشناسی (کلید شیت: tajdid_expert_date)
        if hasattr(t, "expert_date"):
            t.expert_date.setText(str(r.get('tajdid_expert_date','')).strip())

        # 6) تاریخ رأی تجدیدنظر
        if hasattr(t, "verdict_date_tajdid"):
            t.verdict_date_tajdid.setText(str(r.get('verdict_date_tajdid','')).strip())

        # 7) مهلت ۲۵۱ (اگر داخل شیت ذخیره می‌کنی، پر کن؛ در غیر این‌صورت محاسبه‌گر داخلی آن را تنظیم می‌کند)
        dl = str(r.get('deadline_251','') or r.get('objection_deadline_tajdid','')).strip()
        if hasattr(t, "deadline_251") and dl:
            t.deadline_251.setText(dl)

        # 8) درخواست ۲۵۱ انجام شده؟ (RadioGroup obj251_yes / obj251_no)
        obj251 = str(r.get('objection_done_tajdid','')).strip()
        if hasattr(t, "obj251_yes") and hasattr(t, "obj251_no"):
            t.obj251_yes.setAutoExclusive(False); t.obj251_no.setAutoExclusive(False)
            if obj251 in _YES:     t.obj251_yes.setChecked(True);  t.obj251_no.setChecked(False)
            elif obj251 in _NO:    t.obj251_yes.setChecked(False); t.obj251_no.setChecked(True)
            else:                  t.obj251_yes.setChecked(False); t.obj251_no.setChecked(False)
            t.obj251_yes.setAutoExclusive(True);  t.obj251_no.setAutoExclusive(True)

        # 9) تاریخ درخواست ۲۵۱
        if hasattr(t, "obj251_date"):
            t.obj251_date.setText(str(r.get('objection_date_tajdid','')).strip())

        # 10) احراز دبیرخانه شورا (RadioGroup ver_yes / ver_no) یا ComboBox verification_status
        # فیلد در خود پنل به‌صورت پیش‌فرض غیرفعال می‌شود؛ برای prefill باید فعالش کنیم
        with suppress(Exception):
            if hasattr(t, "ver_box"):
                t.ver_box.setEnabled(True)
            if hasattr(t, "verification_status"):
                t.verification_status.setEnabled(True)
                try:
                    t.verification_status.setVisible(True)
                except Exception:
                    pass
        verstat = str(r.get('verification_status','')).strip()
        if hasattr(t, "ver_yes") and hasattr(t, "ver_no"):
            t.ver_yes.setAutoExclusive(False); t.ver_no.setAutoExclusive(False)
            if verstat in _YES:    t.ver_yes.setChecked(True);  t.ver_no.setChecked(False)
            elif verstat in _NO:   t.ver_yes.setChecked(False); t.ver_no.setChecked(True)
            else:                  t.ver_yes.setChecked(False); t.ver_no.setChecked(False)
            t.ver_yes.setAutoExclusive(True);  t.ver_no.setAutoExclusive(True)
        if hasattr(t, "verification_status") and hasattr(t.verification_status, "findText"):
            try:
                idx = t.verification_status.findText(verstat)
                if idx >= 0: t.verification_status.setCurrentIndex(idx)
            except Exception:
                pass

        # 11) تاریخ شورا
        if hasattr(t, "council_date"):
            t.council_date.setText(str(r.get('council_date','')).strip())

    # پایان پنل تجدیدنظر