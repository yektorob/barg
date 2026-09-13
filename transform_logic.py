# -*- coding: utf-8 -*-
# transform_logic.py
"""
منطق تبدیل شیت منبع به قالب ثابت شیت دوم
- بدون هیچ وابستگی به UI
"""

from __future__ import annotations

import re
import pandas as pd

# --- ستون‌های ثابت خروجی مطابق شیت دوم ---
TEMPLATE_COLUMNS = [
    'تاریخ سند *',
    'شماره صورتحساب',
    'کد/شناسه ملی خریدار',
    'نام خریدار ',
    ' تلفن همراه',
    '* کدپستی انبار مبدا',
    'شرح سند',
    '* شناسه کالا',
    '* تعداد/مقدار',
    'مبلغ واحد (ریال)',
    'مبلغ تخفیف (ریال)',
    'سایر اضافات (ریال)',
    'مبلغ مالیات و عوارض (ریال)',
]

# ستون‌هایی که باید در ردیف‌های دوم به بعد خالی شوند (ثابت)
FIXED_BLANK_COLUMNS = {
    'تاریخ سند *',
    'شماره صورتحساب',
    'کد/شناسه ملی خریدار',
    'نام خریدار ',
    ' تلفن همراه',
    '* کدپستی انبار مبدا',
    'شرح سند',
}

# --- عددخوانی نرم برای جمع مالیات/عوارض ---
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

def to_number(s):
    if s is None:
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    t = str(s).strip().translate(PERSIAN_DIGITS)
    t = t.replace(',', '').replace('٬','')
    m = re.search(r'(-?\d+(\.\d+)?)', t)
    return float(m.group(1)) if m else 0.0


# پیشنهاد نگاشت بر اساس نام‌های رایج
SUGGESTIONS = {
    'تاریخ سند *': ['تاریخ'],
    'شماره صورتحساب': ['شماره فاکتور', 'شناسه سند'],
    'کد/شناسه ملی خریدار': ['کد مشتری'],
    'نام خریدار ': ['نام مشتری', 'نام خریدار'],
    'شرح سند': ['نام کالا', 'شرح'],
    '* شناسه کالا': ['شناسه کالا', 'کد کالا'],
    '* تعداد/مقدار': ['تعداد فروش', 'تعداد', 'مقدار'],
    'مبلغ واحد (ریال)': ['قیمت فروش', 'فی فروش'],
    'مبلغ تخفیف (ریال)': [],
    'سایر اضافات (ریال)': ['مبلغ مالیات'],
    'مبلغ مالیات و عوارض (ریال)': ['سایر عوارض', 'مبلغ مالیات و عوارض', 'مالیات و عوارض'],
}

def suggest_mapping(src_cols: list[str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {t: None for t in TEMPLATE_COLUMNS}
    sset = set(map(str, src_cols))
    for tcol, opts in SUGGESTIONS.items():
        for name in opts:
            if name in sset:
                out[tcol] = name
                break
    return out


def build_output(df_src: pd.DataFrame,
                 mapping: dict[str, dict[str, str]],
                 compute_tax_if_missing: bool = True) -> pd.DataFrame:
    """
    mapping: برای هر ستون خروجی یک dict مانند {'source': '<نام ستون در منبع یا "">', 'const': '<رشته ثابت یا "">'}
    خروجی: دیتافریم با ستون‌های TEMPLATE_COLUMNS و خالی‌گذاری ثابت روی ردیف‌های بعدی هر شماره صورتحساب
    """
    src_cols_set = set(map(str, df_src.columns))
    out = pd.DataFrame(index=df_src.index)

    # پر کردن ستون‌ها طبق mapping
    for tcol in TEMPLATE_COLUMNS:
        info = mapping.get(tcol, {'source': '', 'const': ''})
        src_sel = (info.get('source') or '').strip()
        const_v = info.get('const') or ''
        if const_v != "":
            out[tcol] = const_v
        elif src_sel and src_sel != "<خالی>":
            if src_sel not in src_cols_set:
                raise ValueError(f"ستون «{src_sel}» در شیت منبع وجود ندارد.")
            out[tcol] = df_src[src_sel]
        else:
            out[tcol] = ""

    # اگر «مبلغ مالیات و عوارض (ریال)» داده نشد، محاسبه از جمع چند ستون متداول
    tcol_tax = 'مبلغ مالیات و عوارض (ریال)'
    if compute_tax_if_missing and tcol_tax in TEMPLATE_COLUMNS:
        info = mapping.get(tcol_tax, {'source': '', 'const': ''})
        if (info.get('const') == "") and (info.get('source') in ("", None, "<خالی>")):
            parts = ['مبلغ مالیات', 'عوارض', 'عوارض آسیب‌رسان', 'سایر عوارض']
            available = [c for c in parts if c in src_cols_set]
            if available:
                out[tcol_tax] = sum(df_src[c].apply(to_number) for c in available)

    # --- خالی‌گذاری ثابت بر اساس «شماره صورتحساب» ---
    key_col = 'شماره صورتحساب'
    if key_col not in out.columns or out[key_col].eq("").all():
        raise ValueError("برای خالی‌گذاری ثابت، باید ستون «شماره صورتحساب» را معادل‌گذاری کنید.")

    cols_to_blank = [c for c in FIXED_BLANK_COLUMNS if c in out.columns]
    for c in cols_to_blank:
        out[c] = out[c].astype('object')

    groups = out.groupby(key_col, dropna=False, sort=False).groups
    for _, idxes in groups.items():
        idxes = list(idxes)
        if len(idxes) > 1:
            out.loc[idxes[1:], cols_to_blank] = ""

    return out[TEMPLATE_COLUMNS]


def write_output_excel(df_out: pd.DataFrame, out_path: str) -> None:
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
        df_out.to_excel(writer, index=False, sheet_name="خروجی")