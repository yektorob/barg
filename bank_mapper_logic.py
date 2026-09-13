# bank_mapper_logic.py
# -*- coding: utf-8 -*-

import re
import pandas as pd
import jdatetime
from datetime import date as _date
from contextlib import suppress

# ---------------- نرمال‌سازی ----------------
_P2E = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩','01234567890123456789')
ARABIC_FIX = str.maketrans({'ي':'ی','ك':'ک'})

def normalize_text_basic(s: str) -> str:
    s = str(s or '').strip()
    s = s.translate(_P2E).translate(ARABIC_FIX)
    return s

def normalize_for_match(s: str) -> str:
    s = normalize_text_basic(s)
    s = re.sub(r'[\u200c\u200f\u200e\u202a-\u202e\u00a0]+', '', s)  # حذف نیم‌فاصله/RTL marks
    s = re.sub(r'\s+', ' ', s).strip().lower()
    return s

def to_number(x):
    s = normalize_text_basic(x).replace(',', '')
    return pd.to_numeric(s, errors='coerce')

# ---------------- پارسر تاریخ مقاوم ----------------
def parse_persian_date(x):
    if isinstance(x, pd.Timestamp):
        return x
    if isinstance(x, _date):
        return pd.Timestamp(x)

    s = normalize_text_basic(x)
    if not s:
        return pd.NaT

    s = s.split(' ')[0]  # بریدن زمان

    # YYYY/MM/DD یا YYYY-MM-DD یا DD/MM/YYYY
    for sep in ('/', '-'):
        if sep in s:
            parts = s.split(sep)
            if len(parts) == 3 and all(p.isdigit() for p in parts):
                y, m, d = map(int, parts)
                # جلالی
                if 1300 <= y <= 1499:
                    with suppress(Exception):
                        return pd.Timestamp(jdatetime.date(y, m, d).togregorian())
                # میلادی
                if y >= 1500:
                    with suppress(Exception):
                        return pd.Timestamp(year=y, month=m, day=d)
                # DD/MM/YYYY
                if parts[2].isdigit() and int(parts[2]) >= 1500:
                    y2 = int(parts[2]); d2 = int(parts[0]); m2 = int(parts[1])
                    with suppress(Exception):
                        return pd.Timestamp(year=y2, month=m2, day=d2)

    # سریال اکسل
    if s.isdigit() and len(s) <= 5:
        with suppress(Exception):
            return pd.to_datetime('1899-12-30') + pd.to_timedelta(int(s), unit='D')

    # پارسر پیش‌فرض (بدون dayfirst برای حذف هشدار ISO)
    return pd.to_datetime(s, errors='coerce', dayfirst=False)

# ---------------- Helpers ----------------
# تشخیص IBAN (شبا) پس از نرمال‌سازی
_IBAN_RE = re.compile(r'\bIR[0-9A-Z]{6,}\b', re.I)
def has_iban(s: str) -> bool:
    t = (s or '')
    return bool(_IBAN_RE.search(t))

# ---------------- RULES (مپینگ فقط روی ردیف اصلی) ----------------
# نکته: الگوها حداقلی و ایمن‌اند. می‌توانی از بیرون rules سفارشی‌تر تزریق کنی.
RULES_BASE = [
    {'type':'deposit','patterns':['قبض'],'moeen':'7.3.05','tafa':'9000'},
    {'type':'withdrawal','patterns':['قبض'],'moeen':'7.3.05','tafa':'9000'},
    # شاپرک/پایا (فراگیر) → 1.3.02
    {'type':'deposit',
     'patterns': [
         'شاپرک','شاپرك','حواله شاپرک','حواله شاپرك','تسویه شاپرک','تجمیعی شاپرک','shaparak',
         'حواله پایا','واریز پایا','انتقال پایا','paya'
     ],
     'moeen':'1.3.02','tafa':None},

    {'type':'deposit','patterns':['سود','درآمد سود','واریز سود'],'moeen':'6.4.01','tafa':None},
    {'type':'deposit','patterns':['پرداخت حقوق','واریز حقوق'],'moeen':'3.2.01','tafa':None},
    {'type':'deposit','patterns':['عودت کارمزد','عودت کارمزد ساتنا','عودت کارمزد پایا'],'moeen':'7.3.63','tafa':None},
    {'type':'deposit','patterns':['قسط تسهيلات','دريافت وجه'],'moeen':'3.6.01','tafa':None},
{'type':'deposit','patterns':['سند عملیات بانکی'],'moeen':'6.4.01','tafa':None},
    # catch-all واریزی → معین خالی، تفضیلی 2000
    {'type':'deposit','patterns':[],'moeen':'','tafa':'2000'},

    {'type':'withdrawal','patterns':['کارمزد انسداد سپرده'],'moeen':'7.8.01','tafa':None},
    {'type':'withdrawal','patterns':['کارمزد'],'moeen':'7.3.63','tafa':None},  # چون UI فیلد جدا ندارد → خالی می‌گذاریم
    {'type':'withdrawal','patterns':['خرید کالا یا سرویس با کارت'],'moeen':'7.3.25','tafa':None},
    {'type':'withdrawal','patterns':['خرید کالا','خرید از درگاه','خرید','انتقال کارت به کارت','انتقال از کارت'],'moeen':'3.1.02','tafa':None},
    {'type':'withdrawal','patterns':['وصول چک','وصول چك'],'moeen':'3.1.01','tafa':None},
    {'type':'withdrawal','patterns':['ضمانت نامه'],'moeen':'1.6.03','tafa':None},
    {'type':'withdrawal','patterns':['پرداخت قرض','بازپرداخت قرض'],'moeen':'3.2.08','tafa':None},
    {'type':'withdrawal','patterns':['قسط تسهيلات','دريافت وجه'],'moeen':'3.6.01','tafa':None},
# اختیاری: برداشت‌های شاپرک اگر داری
    # catch-all برداشت → هر دو خالی
    {'type':'withdrawal','patterns':[],'moeen':'','tafa':None},
]
# ---------------- تنظیمات تفکیک کارمزد ----------------
FEE_SPLIT_THRESHOLD   = 500_000   # حداقل مبلغ برای فعال شدن تفکیک
FEE_SPLIT_ROUND_BASE  = 100_000      # پایهٔ رُند کردن اصل (مثلاً 100 هزار)
MAX_FEE_AMOUNT        = 500_000      # سقف منطقی کارمزد
def map_main_row(desc_raw: str, rec_type: str, *, include_iban_fallback: bool, rules: list[dict]):
    """
    برگشت: (moeen, tafa) برای «ردیف اصلی».
    استراتژی: اول فقط قوانین با pattern غیرخالی؛ اگر نخورد و IBAN فعال بود (و deposit است) → fallback؛
    بعد اگر هنوز چیزی نبود → قانون پیش‌فرض همان نوع؛ در نهایت ('','').
    """
    if rec_type not in ('deposit','withdrawal'):
        return ('','')

    desc_norm = normalize_for_match(desc_raw)

    # 1) فقط قوانین دارای pattern
    for rule in rules:
        if rule['type'] != rec_type:
            continue
        pats = [normalize_for_match(p) for p in rule['patterns']]
        if pats and any(p in desc_norm for p in pats):
            moeen = rule['moeen'] or ''
            tafa  = '' if (rule['tafa'] is None) else str(rule['tafa'])
            return (moeen, tafa)

    # 2) IBAN fallback (فقط برای واریزی)
    if rec_type == 'deposit' and has_iban(desc_raw):
        # واریزیِ شبا را مثل سایر ورودی‌های بانکی بگذار روی 1.3.02 / 2000
        return ('1.3.01', '')

    # 3) قانون پیش‌فرض همان نوع
    for rule in rules:
        if rule['type'] == rec_type and not rule['patterns']:
            moeen = rule['moeen'] or ''
            tafa  = '' if (rule['tafa'] is None) else str(rule['tafa'])
            return (moeen, tafa)

    return ('','')

# ---------------- هسته پردازش ----------------
def build_records_from_frame(df: pd.DataFrame, vals: dict, default_fee_code: str,
                             *, include_iban_fallback: bool, rules: list[dict]) -> list[dict]:
    """vals: {'تاریخ','شرح','واریز','برداشت','کد تفضیلی','کد کارمزد'}"""

    # فقط ستون‌های موردنیاز
    df = df[[vals['تاریخ'], vals['شرح'], vals['واریز'], vals['برداشت']]].copy()

    # نرمال‌سازی پایه
    df[vals['تاریخ']] = df[vals['تاریخ']].astype(str).str.strip().str.split().str[0]
    df[vals['واریز']] = df[vals['واریز']].apply(to_number).fillna(0.0)
    df[vals['برداشت']] = df[vals['برداشت']].apply(to_number).fillna(0.0)

    all_records = []
    rec_order = 0

    for _, row in df.iterrows():
        d = float(row[vals['واریز']] or 0)      # واریز
        w = float(row[vals['برداشت']] or 0)    # برداشت
        desc_raw = str(row[vals['شرح']])

        # اگر هیچ مبلغی ندارد، رد شو
        if d == 0 and w == 0:
            continue

        # تعیین نوع با fallback
        rec_type = None
        if d > 0 and w == 0:
            rec_type = 'deposit'
        elif w > 0 and d == 0:
            rec_type = 'withdrawal'
        elif d > w:
            rec_type = 'deposit'
        elif w > d:
            rec_type = 'withdrawal'

        # مپینگ اصلی با rules و IBAN
        moeen_main, tafa_main = map_main_row(
            desc_raw, rec_type or '',
            include_iban_fallback=include_iban_fallback,
            rules=rules
        )

        desc_norm = normalize_for_match(desc_raw)

        # برای تفکیک کارمزد
        amt_total = max(d, w)
        split_fee = False          # آیا این رکورد باید اصل/کارمزد بشود؟
        fee_moeen = ''             # معین کارمزد (بانک / پیش‌فرض)

        # قبض → 7.3.05 با تفضیلی 9000 (مثل نسخه قدیمی)
        if 'قبض' in desc_norm:
            moeen_main = '7.3.05'
            tafa_main  = '9000'

        # ریزقوانین تکمیلی قبلی
        if moeen_main == '1.3.02':
            tafa_main = '2000'

        if moeen_main == '3.1.02':
            amt = amt_total
            if amt < 1_500_000:
                moeen_main = '7.3.28'
                tafa_main  = '9000'
            else:
                tafa_main  = '2000'

        if moeen_main == '3.1.01':
            tafa_main = '2000'

        # کارمزد:
        # - اگر رقم درشت و غیرِگرد باشد → تفکیک اصل/کارمزد
        # - در غیر این صورت همان رفتار قدیمی (کل مبلغ = کارمزد)
        if 'کارمزد' in desc_norm:
            fee_bank = str(vals.get('کد کارمزد', '')).strip()
            fee_moeen = fee_bank or default_fee_code or moeen_main

            if (amt_total >= FEE_SPLIT_THRESHOLD) and \
               (amt_total % FEE_SPLIT_ROUND_BASE != 0) and \
               fee_moeen:
                # فعلاً فقط فلگ می‌زنیم؛ خود تفکیک پایین انجام می‌شود
                split_fee = True
            else:
                # حالت کلاسیک: کل مبلغ = کارمزد
                tafa_main = '9000'
                if fee_moeen:
                    moeen_main = fee_moeen

        # قوانین درخواستی:
        # اگر کد معین خالی و شرح شامل «چک» و تفضیلی 2000 → 1.3.01
        if (not str(moeen_main).strip()) and ('چک' in desc_norm) and (str(tafa_main).strip() == '2000'):
            moeen_main = '1.3.01'
        # اگر تفضیلی 2000 و کد معین خالی → 1.3.02 / 2001
        elif (str(tafa_main).strip() == '2000') and (not str(moeen_main).strip()):
            moeen_main = '1.3.02'
            tafa_main  = '2001'
        # اگر هر دو خالی → 3.1.02 / 2000
        elif (not str(moeen_main).strip()) and (not str(tafa_main).strip()):
            moeen_main = '3.1.02'
            tafa_main  = '2000'

        # --- ساخت ردیف‌ها ---

        # سمت بانک: همیشه کل مبلغ در یک ردیف
        line_bank = {
            'تاریخ': row[vals['تاریخ']],
            'شرح':   desc_raw,
            'بدهکار': d,
            'بستانکار': w,
            'کد معین': '1.1.02' if rec_type else '',
            'کد تفضیلی': vals.get('کد تفضیلی', ''),
            'order': rec_order,
        }

        lines_main = []

        # حالت تفکیک اصل / کارمزد
        if split_fee and amt_total > 0 and fee_moeen:
            principal = (amt_total // FEE_SPLIT_ROUND_BASE) * FEE_SPLIT_ROUND_BASE
            fee_amt   = amt_total - principal

            # اگر تقسیم منطقی نبود، برگرد به حالت معمول
            if principal <= 0 or fee_amt <= 0 or fee_amt > MAX_FEE_AMOUNT:
                split_fee = False
            else:
                # ردیف اصل → 3.1.02 / 2000
                line_asal = {
                    'تاریخ': row[vals['تاریخ']],
                    'شرح':   desc_raw,
                    'کد معین': '3.1.02',
                    'کد تفضیلی': '2000',
                    'بدهکار': 0.0,
                    'بستانکار': 0.0,
                    'order': rec_order,
                }

                # ردیف کارمزد → معین کارمزد / 9000
                line_fee = {
                    'تاریخ': row[vals['تاریخ']],
                    'شرح':   desc_raw,
                    'کد معین': fee_moeen,
                    'کد تفضیلی': '9000',
                    'بدهکار': 0.0,
                    'بستانکار': 0.0,
                    'order': rec_order,
                }

                # جهت بدهکار/بستانکار بر اساس نوع رکورد
                if rec_type == 'withdrawal':
                    # برداشت از بانک → بدهکار در طرف مقابل
                    line_asal['بدهکار'] = principal
                    line_fee['بدهکار']  = fee_amt
                    line_bank['بدهکار'] = 0.0
                    line_bank['بستانکار'] = amt_total
                else:
                    # واریز به بانک → بستانکار در طرف مقابل
                    line_asal['بستانکار'] = principal
                    line_fee['بستانکار']  = fee_amt
                    line_bank['بدهکار']   = amt_total
                    line_bank['بستانکار'] = 0.0

                lines_main = [line_asal, line_fee]

        # اگر تفکیک نشد، همان رفتار قبلی: یک ردیف اصلی
        if not split_fee:
            line_main = {
                'تاریخ': row[vals['تاریخ']],
                'شرح':   desc_raw,
                'بدهکار': w,
                'بستانکار': d,
                'کد معین': moeen_main,
                'کد تفضیلی': tafa_main,
                'order': rec_order,
            }
            lines_main = [line_main]

        # بدهکارها قبل از بستانکارها
        pair = lines_main + [line_bank]
        pair.sort(key=lambda r: (r['بدهکار'] == 0,))

        for r in pair:
            r['order'] = rec_order
            all_records.append(r)
            rec_order += 1

    return all_records

def process_banks(banks: list, start_doc: int, start_id: int, output_path: str,
                  default_fee_code: str, *,
                  include_iban_fallback: bool = True,
                  rules: list[dict] | None = None):
    """
    banks: list of dicts, each:
        {'df': DataFrame,
         'vals': {'شیت','تاریخ','شرح','واریز','برداشت','کد تفضیلی','کد کارمزد'}}
    Returns: (DataFrame result, bad_cnt:int)
    """
    if not banks:
        raise ValueError('هیچ بانکی تعریف نشده است.')
    if not output_path:
        raise ValueError('مسیر خروجی خالی است.')

    rules = rules or RULES_BASE

    all_records = []
    for b in banks:
        df = b['df']
        vals = b['vals']
        all_records.extend(
            build_records_from_frame(df, vals, default_fee_code,
                                     include_iban_fallback=include_iban_fallback,
                                     rules=rules)
        )

    if not all_records:
        raise ValueError('هیچ ردیفی تولید نشد. نگاشت ستون‌ها را بررسی کن.')

    merged = pd.DataFrame(all_records)
    merged['__gorder__'] = merged.index  # ترتیب سراسری برای شکستِ قاطی‌شدن زوج‌ها
    merged['تاریخ'] = merged['تاریخ'].apply(parse_persian_date)
    merged['تاریخ'] = pd.to_datetime(merged['تاریخ'], errors='coerce', dayfirst=False)
    bad_cnt = int(merged['تاریخ'].isna().sum())
    merged = merged.dropna(subset=['تاریخ'])
    if merged.empty:
        raise ValueError('همه تاریخ‌ها نامعتبر بودند. مپ ستون تاریخ یا فرمت تاریخ را چک کن.')

    merged.sort_values(['تاریخ','__gorder__'], inplace=True, kind='mergesort')  # سورت پایدار بر اساس تاریخ و ترتیب سراسری
    merged['روز'] = merged['تاریخ'].dt.date

    final_parts = []
    for i, (day, grp) in enumerate(merged.groupby('روز'), start=0):
        voucher_no = int(start_doc) + i
        id_no      = int(start_id) + i
        sub = grp.reset_index(drop=True)
        sub.insert(0, 'ردیف', range(1, len(sub)+1))
        sub.insert(1, 'شناسه', id_no)
        sub.insert(2, 'شماره سند', voucher_no)
        final_parts.append(sub)

    if not final_parts:
        raise ValueError('پس از گروه‌بندی روزانه، چیزی نماند.')

    result = pd.concat(final_parts, ignore_index=True)
    result = result[['ردیف','شناسه','شماره سند','کد معین','کد تفضیلی','تاریخ','شرح','بدهکار','بستانکار']]

    # تاریخ جلالیِ خروجی
    def to_jalali_str(ts):
        if isinstance(ts, pd.Timestamp):
            g = ts.date()
        elif isinstance(ts, _date):
            g = ts
        else:
            return ''
        return jdatetime.date.fromgregorian(date=g).strftime('%Y/%m/%d')

    result['تاریخ'] = result['تاریخ'].apply(to_jalali_str)
    return result, bad_cnt