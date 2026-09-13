# -*- coding: utf-8 -*-
# sales_logic.py
"""
منطق تولید فاکتور فروش (بدون UI)
- توابع جلالی، پارس ورودی‌های فارسی/درصد
- generate_sales برای ساخت دیتافریم‌ها (با هدف‌گذاری مبلغ تصادفی هر فاکتور بین min_total و max_total)
- write_output_excel برای ذخیره خروجی
"""

import re
import math
import random
import pandas as pd
from collections import defaultdict

# === Auto-increment state for invoice/document IDs ============================
import os, json, threading

_SALES_STATE_FILE = os.path.join(os.path.dirname(__file__), "sales_state.json")
DEFAULT_START_INVOICE_NO = int(os.getenv("SALES_START_INVOICE_NO", "1404000000"))
DEFAULT_START_DOC_ID     = int(os.getenv("SALES_START_DOC_ID", "1"))
_STATE_LOCK = threading.Lock()

def _load_sales_state() -> dict:
    try:
        with open(_SALES_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _dump_sales_state(st: dict) -> None:
    tmp = _SALES_STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _SALES_STATE_FILE)

    _SALES_JSON = os.path.join(os.path.dirname(__file__), "sales_state.json")
    """
    برگرداندن مقادیر بعدی.
    - اگر default_invoice=None باشد: برای «شماره فاکتور» هیچ پیش‌فرضی اعمال نمی‌شود؛
      اگر state وجود داشته باشد next = last+1 وگرنه None.
    from core.state import get_state, set_state, migrate_json_file_to_state

    # migrate existing JSON file to DB-backed state if present
    try:
        migrate_json_file_to_state(_SALES_JSON, "sales_state")
    except Exception:
        pass
        if default_invoice is None:
            last_inv = st.get("last_invoice_no")
            next_inv = (int(last_inv) + 1) if last_inv is not None else None
        else:
            di = int(default_invoice)
            last_inv = int(st.get("last_invoice_no", di - 1))
            next_inv = max(di, last_inv + 1)
        # Document logic (always has a floor)
        dd = int(default_docid)
        last_doc = int(st.get("last_document_id", dd - 1))
            st = get_state("sales_state") or {}
        return next_inv, next_doc

def save_last_used(df_sales):
    """
    بیشینهٔ شماره فاکتور/شناسه سند را از df_sales خوانده و در state ذخیره می‌کند.
    نام ستون‌ها پذیرفته: «شماره فاکتور»/InvoiceNo  و  «شناسه سند»/DocumentId
    """
        st = get_state("sales_state") or {}
    st = _load_sales_state()

    def _pick(series):
        if series is None:
            return None
        s = _pd.to_numeric(series, errors="coerce")
        if s.notna().any():
            return int(s.max())
        return None

    inv_col = None
    for name in ("شماره فاکتور", "InvoiceNo"):
        if name in df_sales.columns:
            inv_col = df_sales[name]; break

    doc_col = None
    for name in ("شناسه سند", "DocumentId"):
        if name in df_sales.columns:
            doc_col = df_sales[name]; break

    last_inv_in_df = _pick(inv_col)
    last_doc_in_df = _pick(doc_col)

    if last_inv_in_df is not None:
        st["last_invoice_no"] = int(max(int(st.get("last_invoice_no", 0)), last_inv_in_df))
    if last_doc_in_df is not None:
        st["last_document_id"] = int(max(int(st.get("last_document_id", 0)), last_doc_in_df))

            set_state("sales_state", st)
        _dump_sales_state(st)
# === End state helpers ========================================================

# --- Quantity strategy helper ---
def _pick_qty(max_q: int, strategy: str) -> int:
    """
    انتخاب تعداد بر اساس استراتژی:
      - 'max': همیشه حداکثر ممکن
      - 'min': همیشه 1
      - 'med': حول میانه
      - 'rand': تصادفی بین 1..max_q
    """
    if max_q <= 0:
        return 0
    if strategy == 'max':
        return max_q
    elif strategy == 'min':
        return 1
    # default/random
    return random.randint(1, max_q)


# --------------------- Jalali helpers ---------------------
def is_leap_jalali(year: int) -> bool:
    # ساده‌شده برای تقویم جلالی دورۀ ۳۳ ساله
    return year % 33 in [1, 5, 9, 13, 17, 22, 26, 30]

def next_day_jalali(date_str: str) -> str:
    y, m, d = map(int, date_str.split('/'))
    ml = 31 if m <= 6 else (30 if m <= 11 else (30 if is_leap_jalali(y) else 29))
    if d < ml:
        d += 1
    else:
        d = 1
        if m == 12:
            m, y = 1, y + 1
        else:
            m += 1
    return f"{y:04d}/{m:02d}/{d:02d}"

def all_dates_jalali(start: str, end: str, max_days: int = 200_000):
    """
    تولید لیست تاریخ‌های جلالی شامل ابتدا و انتها، به‌صورت YYYY/MM/DD.
    مستقل از next_day_jalali عمل می‌کند تا از گیرکردن حلقه جلوگیری شود.
    اگر بازه غیرمعقول بزرگ باشد، RuntimeError می‌دهد.
    """
    def _parse(s: str):
        s = s.strip()
        try:
            y, m, d = map(int, s.split("/"))
        except Exception:
            raise ValueError(f"Bad jdate: {s!r} (expected YYYY/MM/DD)")
        return y, m, d

    def _fmt(y: int, m: int, d: int) -> str:
        return f"{y:04d}/{m:02d}/{d:02d}"

    def _days_in_month(y: int, m: int) -> int:
        if m < 1 or m > 12:
            raise ValueError(f"Bad month: {m}")
        mdays = [31,31,31,31,31,31,30,30,30,30,30,29]
        # اسفند کبیسه
        if m == 12 and is_leap_jalali(y):
            return 30
        return mdays[m-1]

    y1, m1, d1 = _parse(start)
    y2, m2, d2 = _parse(end)

    # اعتبارسنجی روز در ماه
    if not (1 <= d1 <= _days_in_month(y1, m1)):
        raise ValueError(f"Bad day in start date: {start}")
    if not (1 <= d2 <= _days_in_month(y2, m2)):
        raise ValueError(f"Bad day in end date: {end}")

    if (y1, m1, d1) > (y2, m2, d2):
        raise ValueError("date_from > date_to")

    out = []
    y, m, d = y1, m1, d1
    count = 0
    while (y, m, d) <= (y2, m2, d2):
        out.append(_fmt(y, m, d))
        d += 1
        dim = _days_in_month(y, m)
        if d > dim:
            d = 1
            m += 1
            if m > 12:
                m = 1
                y += 1

        count += 1
        if count > max_days:
            raise RuntimeError(f"date span too large (> {max_days} days)")
    return out

# --------------------- Utils ---------------------
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

def parse_number_like(val) -> float:
    """هر چیزی شبیه عدد (با ٪، اعداد فارسی، جداکننده هزار) -> float"""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().translate(PERSIAN_DIGITS)
    s = s.replace(',', '').replace('٬','').replace(' ', '')
    m = re.search(r'(-?\d+(\.\d+)?)', s)
    return float(m.group(1)) if m else 0.0

def normalize_tax_percent(raw) -> float:
    """ورودی می‌تواند 60، 60%، 0.6، 0.6% باشد → خروجی بر حسب درصد مثل 60.0"""
    v = parse_number_like(raw)
    if v == 0:
        return 0.0
    return v*100.0 if v <= 1.0 else v

def percent_str(p: float) -> str:
    return f"{int(p)}%" if float(p).is_integer() else f"{p}%"

# --------------------- Core generator ---------------------
def generate_sales(
    df_inv: pd.DataFrame,
    df_cust: pd.DataFrame,
    inv_cols: dict,
    cust_cols: dict,
    start_inv_no: int,
    start_doc_id: int,
    min_total: int,
    max_total: int,
    date_from: str,
    date_to: str,
    duty60_per_unit: float = 0.0,
    duty45_per_unit: float = 0.0,
    qty_strategy: str = 'max',
    harmful_duty_percent=None,
    seed: int | None = None,
):
    """هستهٔ تولید فاکتورها؛ خروجی: (df_sales, df_remaining)
    نکته: برای هر فاکتور یک target تصادفی بین min_total..max_total تعیین می‌شود و اقلام طوری چیده می‌شوند
    که مجموع قبل از مالیات/عوارض تا حد ممکن به آن target نزدیک شود (و هرگز از max_total عبور نکند).
    """

    if seed is not None:
        random.seed(seed)

    # --- سقف تجمیعی فروش برای هر مشتری: برابر با max_total ---
    remaining_by_customer = defaultdict(lambda: float(max_total))
    for _idx, _r in df_cust.iterrows():
        try:
            _code = _r[cust_cols['code']]
            if _code not in remaining_by_customer:
                remaining_by_customer[_code] = float(max_total)
        except Exception:
            pass

    # آماده‌سازی محصولات
    products = []
    for _, r in df_inv.iterrows():
        products.append({
            'code':     r[inv_cols['code']],
            'id':       str(r[inv_cols['id']]),  # شناسه کالا
            'name':     r[inv_cols['name']],
            'price':    float(parse_number_like(r[inv_cols['price']])),
            'buy':      float(parse_number_like(r[inv_cols['buy_price']])),
            'tax_pct':  normalize_tax_percent(r[inv_cols['tax_pct']]),
            'inv':      int(parse_number_like(r[inv_cols['quantity']])),
        })

    # اگر ارزان‌ترین کالا از max_total گران‌تر است اصلاً فاکتوری ساخته نمی‌شود
    cheapest_price_overall = min((p['price'] for p in products if p['inv'] > 0), default=float('inf'))
    if cheapest_price_overall > max_total:
        return pd.DataFrame([]), pd.DataFrame([{'کد کالا': p['code'], 'نام کالا': p['name'], 'موجودی باقیمانده': p['inv']} for p in products])

    date_list = all_dates_jalali(date_from, date_to)
    # نرخ عوارض آسیب‌رسان از ورودی (مثلاً '۲٪' یا '2.5')؛ خالی = ۰٪
    harmful_rate = 0.0
    if harmful_duty_percent is not None and str(harmful_duty_percent).strip():
        harmful_rate = normalize_tax_percent(harmful_duty_percent) / 100.0

    invoices = []
    # تا وقتی موجودی داریم ادامه بده
    while True:
        avail = [p for p in products if p['inv'] > 0]
        if not avail:
            break

        # اگر حتی ارزان‌ترین کالای موجود از min_total هم گران‌تر است، دیگر نمی‌توان فاکتور با حداقل مبلغ ساخت.
        cheapest_now = min(p['price'] for p in avail)
        if cheapest_now > max_total:
            break  # حتی به سقف هم نمی‌رسیم؛ تمام

        # انتخاب مشتری و تاریخ (با رعایت سقف تجمیعی هر مشتری)
        cheapest_now = min(p['price'] for p in avail)
        min_needed = max(float(min_total), float(cheapest_now))

        eligible_mask = df_cust[cust_cols['code']].map(lambda c: remaining_by_customer.get(c, float(max_total)) >= min_needed)
        if not eligible_mask.any():
            break  # دیگر مشتریی با سقف کافی نداریم

        cust = df_cust[eligible_mask].sample().iloc[0]
        inv_date = random.choice(date_list)

        cust_code = cust[cust_cols['code']]
        cap_remaining = float(remaining_by_customer.get(cust_code, float(max_total)))
        invoice_cap = float(min(max_total, cap_remaining))

        # هدف مبلغ تصادفی برای این فاکتور (مجموع قبل از مالیات/عوارض) با کلمپ به سقف باقی‌مانده مشتری
        target_total = random.randint(int(min_total), int(invoice_cap))

        items = []
        total = 0.0
        remaining = target_total

        # برای تنوع، ترتیب کالاهای قابل انتخاب را بهم بزن
        cand = [p for p in avail if p['price'] <= remaining]
        random.shuffle(cand)

        # آستانه توقف: اگر باقی‌مانده کمتر از ارزان‌ترین قیمت بود یا به هدف نزدیک شد
        # tolerance را بر حسب درصدی از target و حداقل یه قیمت ارزان تعیین می‌کنیم
        tolerance = max(0.02 * target_total, min(p['price'] for p in avail))

        # حلقه پر کردن فاکتور تا نزدیک target_total
        safe_guard = 0
        while remaining >= cheapest_now and safe_guard < 1000:
            safe_guard += 1
            # بازبینی کاندیدها بر اساس remaining
            cand = [p for p in avail if p['inv'] > 0 and p['price'] <= remaining]
            if not cand:
                break

            # انتخاب اتفاقی کمی متمایل به کالاهای با قیمت میانه
            p = random.choice(cand)

            # ظرفیت تعداد ممکن باقیمانده
            max_q = min(p['inv'], int(remaining // p['price']))
            if max_q <= 0:
                continue

            q = _pick_qty(max_q, qty_strategy)
            line_total = q * p['price']

            # اگر این انتخاب ما را از سقف عبور می‌دهد، کمترش کن
            # (مجموع فعلی + line_total باید <= min(max_total, invoice_cap))
            hard_remaining = min(max_total - total, invoice_cap - total)
            if line_total > hard_remaining:
                q = max(1, int(hard_remaining // p['price']))
                if q == 0:
                    break
                line_total = q * p['price']

            # اگر بعد از این انتخاب، remaining خیلی کوچک یا منفی می‌شود، بسته به tolerance بپذیر/رد کن
            if remaining - line_total < -1e-9:
                # نمی‌شود برداشت؛ کالای دیگری را امتحان کن
                continue

            # ثبت
            items.append({'prod': p, 'qty': q, 'line_total': line_total})
            total += line_total
            p['inv'] -= q
            remaining = target_total - total

            # نزدیک هدف شدیم؟ تمام
            if abs(remaining) <= tolerance:
                break

        # اگر هنوز به حداقل نرسیده‌ایم، با ارزان‌ترین‌ها پر می‌کنیم (بدون رد شدن از max_total و سقف مشتری)
        if total < min_total:
            # مرتب‌سازی بر اساس قیمت صعودی
            for p in sorted([x for x in avail if x['inv'] > 0], key=lambda x: x['price']):
                if p['price'] > (min(max_total, invoice_cap) - total):
                    continue
                need = min_total - total
                max_q = min(p['inv'], int((min(max_total, invoice_cap) - total) // p['price']))
                if max_q <= 0:
                    continue
                # به‌جای پر کردن دقیق، کمی رندوم تا یکنواخت نشود
                q_upper = max(1, min(max_q, math.ceil(need / p['price'])))
                q = random.randint(1, q_upper)
                line_total = q * p['price']
                if line_total <= 0:
                    continue
                items.append({'prod': p, 'qty': q, 'line_total': line_total})
                total += line_total
                p['inv'] -= q
                if total >= min_total:
                    break

        # اگر فاکتور معتبر نیست، تلاش را متوقف کن
        if not items or total < min_total:
            break

        invoices.append({
            'cust_code': cust[cust_cols['code']],
            'cust_name': cust[cust_cols['name']],
            'date':      inv_date,
            'items':     items,
        })
        # کم کردن از سقف تجمیعی مشتری (بر مبنای جمع کل قبل از مالیات/عوارض)
        try:
            remaining_by_customer[cust_code] = max(0.0, float(remaining_by_customer.get(cust_code, float(max_total))) - float(total))
        except Exception:
            pass

    # شماره‌گذاری
    invoices.sort(key=lambda x: x['date'])
    for idx, inv in enumerate(invoices, start_inv_no):
        inv['inv_no'] = idx
        inv['doc_id'] = start_doc_id + (idx - start_inv_no)

    # ساخت خروجی سطری
    rows = []
    for inv in invoices:
        for it in inv['items']:
            p = it['prod']
            qty = it['qty']
            line_total = it['line_total']

            tax_pct = float(p['tax_pct'])
            vat_amount = line_total * (tax_pct / 100.0)

            is_duty_60 = abs(tax_pct - 60.0) < 1e-6
            is_duty_45 = abs(tax_pct - 45.0) < 1e-6

            duty = 0.0
            if is_duty_60:
                duty = duty60_per_unit * qty
            elif is_duty_45:
                duty = duty45_per_unit * qty

            harmful_duty  = p['buy'] * qty * harmful_rate
            other_duties  = duty + harmful_duty
            final_amount  = line_total + vat_amount + other_duties

            rows.append({
                'شماره فاکتور': inv['inv_no'],
                'شناسه سند':    inv['doc_id'],
                'تاریخ':        inv['date'],
                'کد مشتری':     inv['cust_code'],
                'نام مشتری':    inv['cust_name'],
                'کد کالا':      p['code'],
                'شناسه کالا':   p['id'],
                'نام کالا':     p['name'],
                'قیمت فروش':    line_total / qty,
                'تعداد فروش':   qty,
                'جمع کل':       line_total,
                'فی خرید':      p['buy'],
                'درصد مالیات':  percent_str(tax_pct),
                'مبلغ مالیات':  vat_amount,
                'عوارض':        duty,
                'عوارض آسیب‌رسان': harmful_duty,
                'سایر عوارض':   other_duties,
                'مبلغ نهایی':   final_amount,
            })

    df_sales = pd.DataFrame(rows)

    # افزودن ستون ثابت «کد انبار» با مقدار 1
    if 'کد انبار' not in df_sales.columns:
        df_sales.insert(0, 'کد انبار', 1)
    else:
        df_sales['کد انبار'] = 1

    # اعتبارسنجی: مجموع «جمع کل» هر مشتری از max_total بیشتر نشود
    try:
        if not df_sales.empty and 'جمع کل' in df_sales.columns:
            by_cust = df_sales.groupby('کد مشتری')['جمع کل'].sum()
            violators = by_cust[by_cust > float(max_total)]
            if len(violators) > 0:
                # اگر به هر دلیلی نقض شد، خطا بدهیم تا سریع معلوم شود
                raise ValueError(f"سقف تجمیعی این مشتری‌ها رد شده است: {violators.to_dict()}")
    except Exception as _e:
        # اگر کاربر نخواست قطع شود، می‌تواند این بلوک را حذف کند.
        pass

    rem = [{'کد کالا': p['code'], 'نام کالا': p['name'], 'موجودی باقیمانده': p['inv']}
           for p in products]
    df_remaining = pd.DataFrame(rem)

    return df_sales, df_remaining


def write_output_excel(df_sales: pd.DataFrame, df_remaining: pd.DataFrame, out_path: str) -> None:
    """ذخیرهٔ خروجی در دو شیت با فرمت‌بندی اعداد"""
    money_cols = [
        'قیمت فروش','تعداد فروش','جمع کل','فی خرید',
        'مبلغ مالیات','عوارض','عوارض آسیب‌رسان','سایر عوارض','مبلغ نهایی'
    ]
    for col in money_cols:
        if col in df_sales.columns:
            df_sales[col] = pd.to_numeric(df_sales[col], errors='coerce').round(0)

    with pd.ExcelWriter(out_path, engine='xlsxwriter') as writer:
        df_sales.to_excel(writer,     sheet_name='فاکتورها',         index=False)
        df_remaining.to_excel(writer, sheet_name='موجودی باقیمانده', index=False)

        wb  = writer.book
        sh1 = writer.sheets['فاکتورها']
        num_no_decimal = wb.add_format({'num_format': '#,##0'})
        for colname in money_cols:
            if colname in df_sales.columns:
                idx = df_sales.columns.get_loc(colname)
                sh1.set_column(idx, idx, 16, num_no_decimal)

        if 'موجودی باقیمانده' in df_remaining.columns:
            sh2 = writer.sheets['موجودی باقیمانده']
            i = df_remaining.columns.get_loc('موجودی باقیمانده')
            sh2.set_column(i, i, 16, num_no_decimal)

    # به‌روزرسانی state شناسه‌ها بر اساس خروجی
    try:
        save_last_used(df_sales)
    except Exception:
        pass