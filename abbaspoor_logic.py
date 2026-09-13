# abbaspoor_logic.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import math
import pandas as pd
from typing import List, Tuple, Dict, Any

# --------------------- توابع تاریخ جلالی ---------------------

def jalali_season(date_str: str) -> str:
    """
    ورودی: تاریخ جلالی به‌صورت رشته مثل '1403-07-12' یا '1403/07/12'
    خروجی: یکی از 'بهار'، 'تابستان'، 'پاییز'، 'زمستان'
    """
    if not date_str:
        return 'نامشخص'
    s = str(date_str).strip()
    s = s.replace('/', '-')
    parts = s.split('-')
    if len(parts) != 3:
        return 'نامشخص'
    try:
        month = int(parts[1])
    except Exception:
        return 'نامشخص'
    if 1 <= month <= 3:
        return 'بهار'
    elif 4 <= month <= 6:
        return 'تابستان'
    elif 7 <= month <= 9:
        return 'پاییز'
    elif 10 <= month <= 12:
        return 'زمستان'
    return 'نامشخص'


def _parse_jalali(date_str: str) -> Tuple[int, int, int]:
    """
    ورودی: '1403-07-12' یا '1403/7/1' و غیره؛ خروجی: (year,month,day) به int.
    اگر نشد، (0,0,0).
    """
    if not date_str:
        return 0, 0, 0
    s = str(date_str).strip()
    s = s.replace('/', '-')
    parts = s.split('-')
    if len(parts) != 3:
        return 0, 0, 0
    try:
        y = int(parts[0])
        m = int(parts[1])
        d = int(parts[2])
        return y, m, d
    except Exception:
        return 0, 0, 0


def _format_jalali(y: int, m: int, d: int) -> str:
    """خروجی: 'YYYY-MM-DD' با صفرپرکردن."""
    return f"{y:04d}-{m:02d}-{d:02d}"


def prev_day_jalali(date_str: str) -> str:
    """روز قبل یک تاریخ جلالی (خیلی ساده، بدون تقویم نجومی)."""
    y, m, d = _parse_jalali(date_str)
    if y == 0:
        return date_str
    d -= 1
    if d >= 1:
        return _format_jalali(y, m, d)
    m -= 1
    if m >= 1:
        if m <= 6:
            d = 31
        elif m <= 11:
            d = 30
        else:
            d = 29
        return _format_jalali(y, m, d)
    y -= 1
    if y <= 0:
        return date_str
    m = 12
    d = 29
    return _format_jalali(y, m, d)


def next_day_jalali(date_str: str) -> str:
    """روز بعد یک تاریخ جلالی (ساده)."""
    y, m, d = _parse_jalali(date_str)
    if y == 0:
        return date_str

    def month_len(year: int, month: int) -> int:
        if 1 <= month <= 6:
            return 31
        if 7 <= month <= 11:
            return 30
        return 29 if is_leap_jalali(year) else 29

    d += 1
    ml = month_len(y, m)
    if d <= ml:
        return _format_jalali(y, m, d)
    d = 1
    m += 1
    if m <= 12:
        return _format_jalali(y, m, d)
    y += 1
    m = 1
    return _format_jalali(y, m, d)


def is_leap_jalali(year: int) -> bool:
    return year % 33 in [1, 5, 9, 13, 17, 22, 26, 30]


def to_jalali_str(x) -> str:
    """
    ورودی ممکن است:
    - تاریخ جلالی به صورت رشته
    - عدد / float شبیه 14030712
    - تاریخ میلادی / Timestamp (در این نسخه ساده فقط رشته را برمی‌گردانیم)
    این تابع فقط سعی می‌کند رشته‌ای مثل 'YYYY-MM-DD' از آن بسازد یا خالی برگرداند.
    """
    if x is None:
        return ""
    s = str(x).strip()
    if not s:
        return ""
    s = s.replace('/', '-')
    if '-' in s:
        parts = s.split('-')
        if len(parts) != 3:
            return ""
        try:
            y = int(parts[0])
            m = int(parts[1])
            d = int(parts[2])
            return _format_jalali(y, m, d)
        except Exception:
            return ""
    digits = ''.join(ch for ch in s if ch.isdigit())
    if len(digits) != 8:
        return ""
    try:
        y = int(digits[:4])
        m = int(digits[4:6])
        d = int(digits[6:])
        return _format_jalali(y, m, d)
    except Exception:
        return ""


def _assign_sale_season_for_inventory(inv_date: str) -> str:
    """
    فصل فروش برای موجودی:
    - پیش‌فرض: همان فصل تاریخ ثبت موجودی.
    - اگر روز ثبت 30 یا 31ِ آخر فصل باشد، فصل فروش = فصل روز بعد.
    """
    j = to_jalali_str(inv_date)
    if not j:
        return 'نامشخص'
    y, m, d = _parse_jalali(j)
    if y == 0:
        return 'نامشخص'
    base_season = jalali_season(j)
    if (m in [3, 6, 9, 12]) and (d in [30, 31]):
        nd = next_day_jalali(j)
        next_season = jalali_season(nd)
        return next_season
    return base_season


def _normalize_inventory(df_inv: pd.DataFrame, inv_cols: Dict[str, str]) -> pd.DataFrame:
    """
    نرمال‌سازی اولیه موجودی:
    - تبدیل قیمت و موجودی به int
    - تبدیل تاریخ به شمسی
    """
    df_inv = df_inv.copy()

    code_col = inv_cols.get("code")
    name_col = inv_cols.get("name")
    price_col = inv_cols.get("price")
    qty_col = inv_cols.get("quantity")
    date_col = inv_cols.get("date")

    if price_col and price_col in df_inv.columns:
        df_inv[price_col] = pd.to_numeric(df_inv[price_col], errors="coerce").fillna(0).astype(int)
    if qty_col and qty_col in df_inv.columns:
        df_inv[qty_col] = pd.to_numeric(df_inv[qty_col], errors="coerce").fillna(0).astype(int)

    if date_col and date_col in df_inv.columns:
        df_inv[date_col] = df_inv[date_col].apply(to_jalali_str)

    return df_inv


# --------------------- ابزار تولید خطوط فاکتور ---------------------

def _compute_gcd_of_prices(prices: List[int]) -> int:
    g = 0
    for p in prices:
        try:
            g = math.gcd(g, int(p))
        except Exception:
            continue
    if g == 0:
        return 0
    return g


def _try_build_lines_for_amount(products: List[Dict[str, Any]], day: str, target: int, max_tries: int = 1200):
    """
    تلاش می‌کند با محصولات در دسترس در روز مورد نظر، دقیقا به target برسد.
    هر محصول dict با فیلدهای: code,name,price,inv,start,season
    خروجی: (items, total) که items لیستی از {'prod':p, 'qty':q, 'line_total':...} است.
    اگر دقیق ممکن نشد، بهترین مقدارِ <= target را می‌دهد.
    این نسخه تضمین می‌کند مجموع qty یک کالا در این فراخوانی از inv فعلی‌اش بیشتر نشود.
    """
    # حذف شرط فصل برای اینکه همه کالاها در دسترس باشند
    cand = [p for p in products
            if p['inv'] > 0 and p['start'] <= day and int(p['price']) > 0]
    if not cand:
        return [], 0

    best_items, best_total = [], 0
    best_diff = target  # فاصله تا سقف

    for _ in range(max_tries):
        # موجودی مصرف‌شده‌ی همین تلاش برای هر محصول
        used = {id(p): 0 for p in cand}

        items = []
        remaining = target

        # سعی می‌کنیم با انتخاب تصادفی کالاها و تعدادها، به target نزدیک بشیم
        for _ in range(len(cand) * 3):
            pr = random.choice(cand)
            price = int(pr['price'])
            if price <= 0:
                continue

            # موجودی واقعی قابل مصرف در این تلاش = inv فعلی - چیزی که تا الان در این تلاش ازش برداشتیم
            avail = pr['inv'] - used[id(pr)]
            if avail <= 0:
                continue

            max_q = min(avail, remaining // price if price > 0 else 0)
            if max_q <= 0:
                continue

            q = random.randint(1, max_q)
            line_total = price * q

            # ===== اضافه شده: اگر line_total از remaining بیشتر شد، q رو کم کن =====
            if line_total > remaining:
                q = remaining // price
                if q <= 0:
                    continue
                line_total = price * q

            items.append({'prod': pr, 'qty': q, 'line_total': line_total})
            used[id(pr)] += q
            remaining -= line_total

            if remaining <= 0:
                break

        total = sum(it['line_total'] for it in items)
        
        # ===== شرط جدید: total نباید از target بیشتر باشد =====
        if total <= 0 or total > target:
            continue

        diff = target - total
        if 0 <= diff < best_diff:
            best_diff = diff
            best_items = items
            best_total = total
            if best_diff == 0:
                break

    if best_total <= 0:
        return [], 0

    # قبل از کم‌کردن موجودی، یک چک سفت: اگر هرجا قرار بود منفی بشه، همون‌جا کرش کن تا بفهمیم مشکل از کجاست
    for it in best_items:
        p = it['prod']
        q = it['qty']
        if q > p['inv']:
            raise ValueError(f"Negative inventory would happen for code={p.get('code')} inv={p['inv']} qty={q}")
        p['inv'] -= q

    return best_items, best_total

# --------------------- شاپرک ---------------------

def _normalize_shaparak(
    df_shap: pd.DataFrame,
    shap_cols: Dict[str, str],
    type_filter: str = None
) -> List[Tuple[str, int]]:
    """
    نرمال‌سازی شاپرک.
    اگر type_filter یکی از "شاپرک" یا "انتقالی" باشد و ستون نوع تعریف شده باشد،
    فقط همان نوع را برمی‌گرداند.
    خروجی: لیست [(date_str, credit_int)] مرتب‌شده بر اساس تاریخ شاپرک.
    """
    col_d = shap_cols.get('date')
    col_c = shap_cols.get('credit')
    col_t = shap_cols.get('type')

    if not col_d or not col_c:
        return []

    tmp: List[Tuple[str, int]] = []
    for _, r in df_shap.iterrows():
        # تاریخ
        try:
            d = to_jalali_str(r[col_d])
        except Exception:
            d = ""
        if not d:
            continue

        # مبلغ
        try:
            c = int(r[col_c])
        except Exception:
            try:
                c = int(float(r[col_c]))
            except Exception:
                continue

        # فیلتر نوع (در صورت وجود)
        if type_filter is not None and col_t is not None:
            raw_type = str(r.get(col_t, "")).strip()
            norm = (
                raw_type.replace("ي", "ی")
                        .replace("ك", "ک")
                        .replace(" ", "")
            )
            if type_filter == "شاپرک":
                if "انتقال" in norm:
                    continue
            elif type_filter == "انتقالی":
                if "انتقال" not in norm:
                    continue
        elif type_filter == "انتقالی" and col_t is None:
            continue

        tmp.append((d, c))

    tmp.sort(key=lambda t: t[0])
    return tmp


# --------------------- تولید فاکتورها ---------------------

def generate_sales(
    df_inv: pd.DataFrame,
    df_cust: pd.DataFrame,
    df_shap: pd.DataFrame,
    inv_cols: Dict[str, str],
    cust_cols: Dict[str, str],
    shap_cols: Dict[str, str],
    start_inv_no: int,
    start_doc_id: int,
    min_amount_shap: int = None,
    max_amount_shap: int = None,
    min_amount_transfer: int = None,
    max_amount_transfer: int = None,
) -> pd.DataFrame:

    df_inv = _normalize_inventory(df_inv, inv_cols)

    # -------- محصولات (بدون مالیات) --------
    products: List[Dict[str, Any]] = []
    for _, r in df_inv.iterrows():
        jdate = to_jalali_str(r[inv_cols["date"]])
        start = next_day_jalali(jdate)
        season = _assign_sale_season_for_inventory(jdate)

        products.append(
            {
                "code": r[inv_cols["code"]],
                "name": r[inv_cols["name"]],
                "price": int(r[inv_cols["price"]]),
                "inv": int(r[inv_cols["quantity"]]),
                "start": start,
                "season": season,
            }
        )

    # -------- ساخت jobها از شاپرک --------
    col_d = shap_cols.get("date")
    col_c = shap_cols.get("credit")
    col_t = shap_cols.get("type")

    if not col_d or not col_c or col_d not in df_shap.columns or col_c not in df_shap.columns:
        return pd.DataFrame()

    df_shap = df_shap.copy()
    df_shap[col_c] = pd.to_numeric(df_shap[col_c], errors="coerce").fillna(0)

    day_targets: Dict[str, int] = {}
    day_first_idx: Dict[str, int] = {}
    transfer_jobs: List[Dict[str, Any]] = []

    for idx, r in df_shap.iterrows():
        credit = r[col_c]
        if pd.isna(credit):
            continue
        try:
            c = int(round(float(credit)))
        except Exception:
            continue
        if c <= 0:
            continue

        raw_date = r[col_d]
        sale_day = to_jalali_str(raw_date)
        if not sale_day:
            continue

        ttype = "شاپرک"
        if col_t and col_t in df_shap.columns:
            raw_type = str(r.get(col_t, "")).strip()
            norm = raw_type.replace("ي", "ی").replace("ك", "ک").replace(" ", "")
            if "انتقال" in norm:
                ttype = "انتقالی"

        if ttype == "انتقالی":
            transfer_jobs.append({"day": sale_day, "kind": "transfer", "amount": c, "idx": idx})
        else:
            if sale_day not in day_targets:
                day_targets[sale_day] = 0
                day_first_idx[sale_day] = idx
            day_targets[sale_day] += c
            if idx < day_first_idx[sale_day]:
                day_first_idx[sale_day] = idx

    shap_jobs: List[Dict[str, Any]] = []
    for day, total in day_targets.items():
        if total <= 0:
            continue
        shap_jobs.append({"day": day, "kind": "shaparak", "amount": int(total), "idx": day_first_idx.get(day, 10**9)})

    jobs = shap_jobs + transfer_jobs
    jobs.sort(key=lambda j: (j["day"], j["idx"]))

    invoices: List[Dict[str, Any]] = []
    inv_no = int(start_inv_no)
    doc_id = int(start_doc_id)
    df_cust = df_cust.copy().reset_index(drop=True)
    cust_indices = list(df_cust.index)
    random.shuffle(cust_indices)
    cust_pos = 0

    def _next_customer():
        nonlocal cust_pos
        if cust_pos >= len(cust_indices):
            raise RuntimeError(
                "تعداد فاکتورها از تعداد مشتری‌ها بیشتر شد؛ بدون تکرار کد مشتری نمی‌تونم فاکتور بیشتری بسازم."
            )
        idx = cust_indices[cust_pos]
        cust_pos += 1
        return df_cust.loc[idx]

    # -------- پردازش jobها --------
    for job in jobs:
        day = job["day"]
        target = int(job["amount"])
        if target <= 0:
            continue

        # انتخاب حداقل و حداکثر بر اساس نوع
        if job["kind"] == "transfer":
            min_amount = min_amount_transfer
            max_amount = max_amount_transfer
        else:  # shaparak
            min_amount = min_amount_shap
            max_amount = max_amount_shap

        # --- انتقالی: هر job یک فاکتور ---
        if job["kind"] == "transfer":
            # اگر محدودیت رنج برای انتقالی تعریف شده، از آن استفاده کن
            if min_amount is not None and max_amount is not None and min_amount > 0 and max_amount > 0:
                # اگر مبلغ از محدوده خارج است، به چند فاکتور تقسیم کن
                if target > max_amount:
                    # تقسیم به چند فاکتور
                    remaining = target
                    while remaining > 0:
                        desired = min(max_amount, remaining)
                        if desired < min_amount and remaining < min_amount:
                            # اگر باقیمانده کمتر از حداقل است، کل را در یک فاکتور بگذار
                            desired = remaining
                        
                        items, total = _try_build_lines_for_amount(products, day, desired, max_tries=1500)
                        if total <= 0:
                            break
                            
                        cust = _next_customer()
                        invoices.append(
                            {
                                "inv_no": inv_no,
                                "doc_id": doc_id,
                                "date": day,
                                "season": jalali_season(day),
                                "cust_code": cust[cust_cols["code"]],
                                "cust_name": cust[cust_cols["name"]],
                                "items": items,
                                "total": total,
                                "type": "انتقالی",
                                "shap_amount": target,
                            }
                        )
                        inv_no += 1
                        doc_id += 1
                        remaining -= total
                        if remaining <= 0:
                            break
                    continue
                elif target < min_amount:
                    # اگر مبلغ کمتر از حداقل است، یک فاکتور با همان مبلغ
                    pass  # ادامه می‌دهیم تا فاکتور با همان مبلغ ساخته شود
            
            items, total = _try_build_lines_for_amount(products, day, target, max_tries=1500)
            if total <= 0:
                continue

            cust = _next_customer()
            invoices.append(
                {
                    "inv_no": inv_no,
                    "doc_id": doc_id,
                    "date": day,
                    "season": jalali_season(day),
                    "cust_code": cust[cust_cols["code"]],
                    "cust_name": cust[cust_cols["name"]],
                    "items": items,
                    "total": total,
                    "type": "انتقالی",
                    "shap_amount": target,
                }
            )
            inv_no += 1
            doc_id += 1
            continue

        # --- شاپرک: امکان تقسیم به چند فاکتور با min/max ---
        remaining = target
        use_range = (
            min_amount is not None
            and max_amount is not None
            and min_amount > 0
            and max_amount > 0
        )

        if not use_range:
            items, total = _try_build_lines_for_amount(products, day, remaining, max_tries=1500)
            if total <= 0:
                continue
            inv_date = prev_day_jalali(day)
            cust = _next_customer()
            invoices.append(
                {
                    "inv_no": inv_no,
                    "doc_id": doc_id,
                    "date": inv_date,
                    "season": jalali_season(inv_date),
                    "cust_code": cust[cust_cols["code"]],
                    "cust_name": cust[cust_cols["name"]],
                    "items": items,
                    "total": total,
                    "type": "شاپرک",
                    "shap_amount": target,
                }
            )
            inv_no += 1
            doc_id += 1
            continue

       # حالت رنج با منطق جدید (تولید مبالغ متغیر)
        day_season = jalali_season(day)
        day_prices = [
            p["price"]
            for p in products
            if p.get("inv", 0) > 0 and p.get("start") <= day and p.get("season") == day_season
        ]
        g = _compute_gcd_of_prices(day_prices) or 1

        eff_min = ((int(min_amount) + g - 1) // g) * g
        eff_max = (int(max_amount) // g) * g
        if eff_max <= 0:
            eff_max = eff_min
        if eff_min > eff_max:
            eff_min = eff_max

        def _pick_desired(rem: int) -> int:
            """
            انتخاب مبلغ بین eff_min و eff_max به صورت تصادفی
            با رعایت اینکه باقیمانده بعد از کسر، کمتر از eff_min نباشد
            """
            # اگر باقیمانده خودش کمتر از eff_max هست
            if rem <= eff_max:
                # اگر از eff_min بزرگتره، خودش رو برگردون
                if rem >= eff_min:
                    return rem
                else:
                    # اگر از eff_min کمتره، همون رو برگردون (آخرین فاکتور)
                    return rem
            
            # محاسبه حداکثر مقداری که میتونیم برداریم تا باقیمانده حداقل eff_min باشه
            max_allowed = rem - eff_min
            
            # اگر حداکثر مجاز بیشتر از eff_max هست، بین eff_min و eff_max انتخاب کن
            if max_allowed >= eff_max:
                return random.randint(eff_min, eff_max)
            else:
                # وگرنه بین eff_min و max_allowed انتخاب کن
                return random.randint(eff_min, max_allowed)

        # ===== متغیر برای شمارش تلاش‌های ناموفق =====
        failed_attempts = 0
        max_failed_attempts = 10

        while remaining >= eff_min and remaining > 0:
            # اگر تعداد تلاش‌های ناموفق زیاد شد، از حلقه خارج شو
            if failed_attempts >= max_failed_attempts:
                # اگر هنوز باقیمانده قابل توجهی هست، با یک فاکتور آخرین تلاش رو بکن
                if remaining > 0:
                    items, total = _try_build_lines_for_amount(products, day, remaining, max_tries=3000)
                    if total > 0:
                        inv_date = prev_day_jalali(day)
                        cust = _next_customer()
                        invoices.append(
                            {
                                "inv_no": inv_no,
                                "doc_id": doc_id,
                                "date": inv_date,
                                "season": jalali_season(inv_date),
                                "cust_code": cust[cust_cols["code"]],
                                "cust_name": cust[cust_cols["name"]],
                                "items": items,
                                "total": total,
                                "type": "شاپرک",
                                "shap_amount": total,
                            }
                        )
                        inv_no += 1
                        doc_id += 1
                        remaining -= total
                break
            
            desired = _pick_desired(remaining)
            
            # اطمینان از اینکه desired از remaining بیشتر نباشه
            desired = min(desired, remaining)
            
            # اگر desired از eff_min کمتر شد، از حلقه خارج شو
            if desired < eff_min:
                break
            
            # ===== تلاش برای ساخت فاکتور با تعداد تلاش بیشتر =====
            items, total = _try_build_lines_for_amount(products, day, desired, max_tries=3000)
            
            # ===== بررسی رعایت رنج =====
            # شرط اول: total باید بین eff_min و eff_max باشد (و از desired بیشتر نباشد)
            if total <= 0 or total > desired:
                failed_attempts += 1
                # اگر total از desired بیشتر شد، یکبار دیگر با مقدار کمتر تلاش کن
                if total > desired:
                    # سعی کن با نصف مقدار قبلی
                    smaller_desired = max(eff_min, desired // 2)
                    if smaller_desired < desired:
                        items, total = _try_build_lines_for_amount(products, day, smaller_desired, max_tries=3000)
                        if total > 0 and total <= smaller_desired and eff_min <= total <= eff_max:
                            # موفق شد
                            pass
                        else:
                            continue
                    else:
                        continue
                else:
                    continue
            
            # شرط دوم: total نباید از eff_max بیشتر باشد
            if total > eff_max:
                failed_attempts += 1
                continue
            
            # شرط سوم: اگر total از eff_min کمتر است ولی remaining خیلی کم است، قبول کن
            if total < eff_min and remaining > eff_min:
                failed_attempts += 1
                continue
            # ===== اگر همه چیز درست بود، فاکتور رو اضافه کن =====
            inv_date = prev_day_jalali(day)
            cust = _next_customer()
            invoices.append(
                {
                    "inv_no": inv_no,
                    "doc_id": doc_id,
                    "date": inv_date,
                    "season": jalali_season(inv_date),
                    "cust_code": cust[cust_cols["code"]],
                    "cust_name": cust[cust_cols["name"]],
                    "items": items,
                    "total": total,
                    "type": "شاپرک",
                    "shap_amount": total,
                }
            )
            inv_no += 1
            doc_id += 1
            remaining -= total
            failed_attempts = 0  # ریست کردن شمارنده تلاش‌های ناموفق
    # -------- تخت کردن فاکتورها به df_sales --------
    rows: List[Dict[str, Any]] = []
    for inv in invoices:
        for it in inv["items"]:
            p = it["prod"]
            rows.append(
                {
                    "شماره فاکتور": inv["inv_no"],
                    "شناسه سند": inv["doc_id"],
                    "تاریخ": inv["date"],
                    "فصل": inv["season"],
                    "نوع": inv.get("type", ""),
                    "کد مشتری": inv["cust_code"],
                    "نام مشتری": inv["cust_name"],
                    "کد کالا": p["code"],
                    "نام کالا": p["name"],
                    "قیمت فروش": int(p["price"]),
                    "فی پایه موجودی": int(p["price"]),
                    "تعداد فروش": int(it["qty"]),
                    "جمع کل": int(it["line_total"]),
                    "مبلغ انتقالی": int(inv.get("shap_amount", 0)),
                }
            )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # عددی‌سازی
    df["تعداد فروش"] = pd.to_numeric(df["تعداد فروش"], errors="coerce").fillna(0).astype(int)
    df["قیمت فروش"] = pd.to_numeric(df["قیمت فروش"], errors="coerce").fillna(0).astype(int)
    df["فی پایه موجودی"] = pd.to_numeric(df["فی پایه موجودی"], errors="coerce").fillna(0).astype(int)
    df["مبلغ انتقالی"] = pd.to_numeric(df.get("مبلغ انتقالی", 0), errors="coerce").fillna(0).astype(int)

    # محاسبه جمع کالا و جمع کل (بدون مالیات)
    df["جمع کالا"] = (df["قیمت فروش"] * df["تعداد فروش"]).round().astype(int)
    df["جمع کل"] = df["جمع کالا"].astype(int)

    # ستون اختلاف: شروع از صفر
    df["اختلاف"] = 0

    # ۲) اصلاح فاکتورهای انتقالی: اختلاف به نسبت تعداد فروش
    if "مبلغ انتقالی" in df.columns:
        mask_transfer = df["نوع"] == "انتقالی"
        if mask_transfer.any():
            inv_diff = (
                df[mask_transfer]
                .groupby("شماره فاکتور", as_index=False)
                .agg({"جمع کل": "sum", "مبلغ انتقالی": "first"})
            )
            inv_diff["اختلاف"] = inv_diff["مبلغ انتقالی"] - inv_diff["جمع کل"]

            for _, row in inv_diff.iterrows():
                inv_no_val = row["شماره فاکتور"]
                diff_gross = int(row["اختلاف"])
                if diff_gross == 0:
                    continue

                sub_mask = (df["شماره فاکتور"] == inv_no_val) & (df["نوع"] == "انتقالی")
                sub = df[sub_mask]
                if sub.empty:
                    continue

                valid_idx = list(sub.index)
                if len(valid_idx) == 0:
                    continue

                # جمع کل تعداد فروش آیتم‌های این فاکتور
                total_qty = sum(df.at[idx2, "تعداد فروش"] for idx2 in valid_idx)
                if total_qty == 0:
                    continue

                for idx2 in valid_idx:
                    qty_i = df.at[idx2, "تعداد فروش"]
                    # سهم این آیتم از اختلاف به نسبت تعداد فروش
                    share = (qty_i / total_qty) * diff_gross
                    share = int(round(share))

                    # اعمال اختلاف به قیمت فروش
                    base_unit = df.at[idx2, "فی پایه موجودی"]
                    delta_unit = share / qty_i if qty_i > 0 else 0
                    df.at[idx2, "قیمت فروش"] = base_unit + delta_unit
                    df.at[idx2, "اختلاف"] = share

            # بازمحاسبه بعد از اصلاح
            df["قیمت فروش"] = pd.to_numeric(df["قیمت فروش"], errors="coerce").fillna(0).astype(int)
            df["جمع کالا"] = (df["قیمت فروش"] * df["تعداد فروش"]).round().astype(int)
            df["جمع کل"] = df["جمع کالا"].astype(int)
            # ===== اضافه شدن این بخش جدید =====
        # بازمحاسبه اختلاف بعد از اصلاح قیمت‌ها
            df["اختلاف"] = 0  # ریست کردن
            for inv_no_val in df[mask_transfer]["شماره فاکتور"].unique():
                mask_inv = (df["شماره فاکتور"] == inv_no_val) & (df["نوع"] == "انتقالی")
                if mask_inv.any():
                    total_inv = df.loc[mask_inv, "جمع کل"].sum()
                    shap_amount = df.loc[mask_inv, "مبلغ انتقالی"].iloc[0]
                    diff = shap_amount - total_inv
                    if diff != 0:
                        # پخش اختلاف به نسبت جمع کل
                        for idx in df[mask_inv].index:
                            share = (df.at[idx, "جمع کل"] / total_inv) * diff if total_inv > 0 else 0
                            df.at[idx, "اختلاف"] = int(round(share))
            # ===== پایان بخش جدید =====

    # ۳) شاپرک: اختلاف روز روی یک فاکتور، به نسبت تعداد فروش
    mask_shap = df["نوع"] == "شاپرک"
    if mask_shap.any():
        days = sorted(df.loc[mask_shap, "تاریخ"].unique())
        for day in days:
            mask_day = mask_shap & (df["تاریخ"] == day)
            sub_day = df[mask_day]
            if sub_day.empty:
                continue

            total_invoices = sub_day["جمع کل"].sum()
            next_day = next_day_jalali(day)
            shap_next = int(day_targets.get(next_day, 0))

            if shap_next == 0:
                continue

            diff_gross = shap_next - total_invoices
            diff_gross = int(diff_gross)
            if diff_gross == 0:
                continue

            # انتخاب یک فاکتور از روی بیشترین جمع کالا
            row_idx_max = sub_day["جمع کالا"].idxmax()
            inv_no_val = df.at[row_idx_max, "شماره فاکتور"]

            mask_inv = mask_day & (df["شماره فاکتور"] == inv_no_val)
            sub_inv = df[mask_inv]
            if sub_inv.empty:
                continue

            valid_idx = list(sub_inv.index)
            total_qty = sum(df.at[idx2, "تعداد فروش"] for idx2 in valid_idx)
            if total_qty == 0:
                continue

            for idx2 in valid_idx:
                qty_i = df.at[idx2, "تعداد فروش"]
                share = (qty_i / total_qty) * diff_gross
                share = int(round(share))

                base_unit = df.at[idx2, "فی پایه موجودی"]
                delta_unit = share / qty_i if qty_i > 0 else 0
                df.at[idx2, "قیمت فروش"] = base_unit + delta_unit
                df.at[idx2, "اختلاف"] = share

        # بازمحاسبه بعد از اصلاح شاپرک‌ها
        df["قیمت فروش"] = pd.to_numeric(df["قیمت فروش"], errors="coerce").fillna(0).astype(int)
        df["جمع کالا"] = (df["قیمت فروش"] * df["تعداد فروش"]).round().astype(int)
        df["جمع کل"] = df["جمع کالا"].astype(int)
        # ===== اضافه شدن این بخش جدید =====
        # بازمحاسبه اختلاف بعد از اصلاح قیمت‌ها
        for day in days:
            mask_day = mask_shap & (df["تاریخ"] == day)
            sub_day = df[mask_day]
            if sub_day.empty:
                continue
                
            total_invoices = sub_day["جمع کل"].sum()
            next_day = next_day_jalali(day)
            shap_next = int(day_targets.get(next_day, 0))
            
            if shap_next == 0:
                continue
                
            diff_gross = shap_next - total_invoices
            if diff_gross == 0:
                continue
                
            # پیدا کردن فاکتوری که اختلاف روش اعمال شده
            # (همون فاکتوری که قبلاً انتخاب شده)
            row_idx_max = sub_day["جمع کالا"].idxmax()
            inv_no_val = df.at[row_idx_max, "شماره فاکتور"]
            mask_inv = (df["شماره فاکتور"] == inv_no_val) & mask_day
            
            if mask_inv.any():
                total_inv = df.loc[mask_inv, "جمع کل"].sum()
                # پخش اختلاف به نسبت جمع کل آیتم‌ها
                for idx in df[mask_inv].index:
                    share = (df.at[idx, "جمع کل"] / total_inv) * diff_gross if total_inv > 0 else 0
                    df.at[idx, "اختلاف"] = int(round(share))
        # ===== پایان بخش جدید =====


    # ۴) ترتیب ستون‌ها
    cols_order = [
        "شماره فاکتور",
        "شناسه سند",
        "تاریخ",
        "فصل",
        "نوع",
        "کد مشتری",
        "نام مشتری",
        "کد کالا",
        "نام کالا",
        "قیمت فروش",
        "فی پایه موجودی",
        "تعداد فروش",
        "جمع کالا",
        "جمع کل",
        "مبلغ انتقالی",
        "اختلاف",
    ]
    cols_final = [c for c in cols_order if c in df.columns]
    return df[cols_final].copy()


# ====================== اختلاف روزانه ======================

def build_daily_diff(df_sales: pd.DataFrame, df_shap: pd.DataFrame, shap_cols: Dict[str, str]) -> pd.DataFrame:
    """
    اختلاف روزانه به تفکیک نوع (شاپرک / انتقالی):

    - برای type = شاپرک:
        * مبلغ شاپرک از df_shap خوانده می‌شود.
        * تاریخ فاکتور = روز قبل از تاریخ شاپرک (prev_day_jalali).
        * در df_sales ردیف‌های نوع شاپرک در همان تاریخ جمع می‌شوند.

    - برای type = انتقالی:
        * مبلغ انتقالی از df_shap خوانده می‌شود.
        * تاریخ فاکتور = خود تاریخ شاپرک.
        * در df_sales ردیف‌های نوع انتقالی در همان تاریخ جمع می‌شوند.

    خروجی: تاریخ، نوع، جمع فاکتورها، مبلغ شاپرک (روز بعد)، اختلاف
    """
    if df_sales is None or df_sales.empty:
        return pd.DataFrame(columns=["تاریخ", "نوع", "جمع فاکتورها", "مبلغ شاپرک (روز بعد)", "اختلاف"])

    if df_shap is None or df_shap.empty:
        tmp = (
            df_sales.groupby(["تاریخ", "نوع"], as_index=False)["جمع کل"]
            .sum()
            .rename(columns={"جمع کل": "جمع فاکتورها"})
        )
        tmp["مبلغ شاپرک (روز بعد)"] = 0
        tmp["اختلاف"] = -tmp["جمع فاکتورها"]
        return tmp

    col_d = shap_cols.get("date")
    col_c = shap_cols.get("credit")
    col_t = shap_cols.get("type")

    if not col_d or not col_c or col_d not in df_shap.columns or col_c not in df_shap.columns:
        tmp = (
            df_sales.groupby(["تاریخ", "نوع"], as_index=False)["جمع کل"]
            .sum()
            .rename(columns={"جمع کل": "جمع فاکتورها"})
        )
        tmp["مبلغ شاپرک (روز بعد)"] = 0
        tmp["اختلاف"] = -tmp["جمع فاکتورها"]
        return tmp

    shap_rows: List[Dict[str, Any]] = []
    df_s = df_shap.copy()
    df_s[col_c] = pd.to_numeric(df_s[col_c], errors="coerce").fillna(0)

    for _, r in df_s.iterrows():
        credit = r[col_c]
        if credit == 0 or pd.isna(credit):
            continue
        try:
            c_int = int(round(float(credit)))
        except Exception:
            continue

        raw_date = r[col_d]
        d_jalali = to_jalali_str(raw_date)
        if not d_jalali:
            continue

        ttype = "شاپرک"
        if col_t and col_t in df_s.columns:
            raw_type = str(r.get(col_t, "")).strip()
            norm = raw_type.replace("ي", "ی").replace("ك", "ک").replace(" ", "")
            if "انتقال" in norm:
                ttype = "انتقالی"

        if ttype == "شاپرک":
            inv_day = prev_day_jalali(d_jalali)
        else:
            inv_day = d_jalali

        shap_rows.append(
            {
                "تاریخ": inv_day,
                "نوع": ttype,
                "مبلغ شاپرک (روز بعد)": c_int,
            }
        )

    if shap_rows:
        shap_df = (
            pd.DataFrame(shap_rows)
            .groupby(["تاریخ", "نوع"], as_index=False)["مبلغ شاپرک (روز بعد)"]
            .sum()
        )
    else:
        shap_df = pd.DataFrame(columns=["تاریخ", "نوع", "مبلغ شاپرک (روز بعد)"])

    # جمع فاکتورها از df_sales (بعد از اصلاح فی)
    df_sales = df_sales.copy()
    df_sales["جمع کل"] = pd.to_numeric(df_sales["جمع کل"], errors="coerce").fillna(0)
    sales_sum = (
        df_sales.groupby(["تاریخ", "نوع"], as_index=False)["جمع کل"]
        .sum()
        .rename(columns={"جمع کل": "جمع فاکتورها"})
    )

    out = pd.merge(sales_sum, shap_df, on=["تاریخ", "نوع"], how="outer").fillna(0)

    if "جمع فاکتورها" not in out.columns:
        out["جمع فاکتورها"] = 0
    if "مبلغ شاپرک (روز بعد)" not in out.columns:
        out["مبلغ شاپرک (روز بعد)"] = 0

    out["جمع فاکتورها"] = out["جمع فاکتورها"].astype(int)
    out["مبلغ شاپرک (روز بعد)"] = out["مبلغ شاپرک (روز بعد)"].astype(int)
    out["اختلاف"] = out["مبلغ شاپرک (روز بعد)"] - out["جمع فاکتورها"]

    try:
        out = out.sort_values(["تاریخ", "نوع"]).reset_index(drop=True)
    except Exception:
        pass

    return out


def build_remaining_inventory_sheet(df_inv: pd.DataFrame,
                                    df_sales: pd.DataFrame,
                                    inv_cols: Dict[str, str]) -> pd.DataFrame:
    """
    موجودی باقیمانده بر اساس:
      - مچ کردن فروش با (کد کالا + قیمت فروش پایه برای موجودی)
      - پخش فروش داخل هر (کد، قیمت) به صورت FIFO روی تاریخ خرید

    ستون‌های نهایی:
      کد کالا، نام کالا، تاریخ موجودی، قیمت، تعداد اولیه، فروش، باقیمانده، وضعیت

    ⚠️ نکته:
      اگر در df_sales ستونی به نام «فی پایه موجودی» وجود داشته باشد،
      برای مچ با موجودی از همان استفاده می‌شود.
      در غیر این‌صورت، از «قیمت فروش» استفاده می‌کند.
    """

    CODE = inv_cols['code']
    NAME = inv_cols['name']
    INVQ = inv_cols['quantity']
    PRICE = inv_cols['price']
    DATE = inv_cols.get('date')

    # اگر موجودی خالی است
    if df_inv is None or df_inv.empty:
        cols = [c for c in [CODE, NAME, DATE, PRICE, INVQ, 'فروش', 'باقیمانده', 'وضعیت'] if c]
        return pd.DataFrame(columns=cols)

    df_inv = df_inv.copy()

    # نرمال‌سازی عددی
    df_inv[INVQ] = pd.to_numeric(df_inv[INVQ], errors='coerce').fillna(0).astype(int)
    df_inv[PRICE] = pd.to_numeric(df_inv[PRICE], errors='coerce').fillna(0).astype(int)

    # نرمال‌سازی تاریخ موجودی
    if DATE and DATE in df_inv.columns:
        df_inv[DATE] = df_inv[DATE].apply(to_jalali_str)
    else:
        DATE = None

    # اگر فروش نداریم → همون موجودی، بدون فروش
    if df_sales is None or df_sales.empty:
        out = df_inv.copy()
        out['فروش'] = 0
        out['باقیمانده'] = out[INVQ].astype(int)
        out['وضعیت'] = out['باقیمانده'].apply(lambda x: 'تمام شده' if x <= 0 else 'باقی مانده')

        sort_cols = [CODE]
        if DATE:
            sort_cols.append(DATE)
        sort_cols.append(PRICE)
        try:
            out = out.sort_values(sort_cols)
        except Exception:
            pass

        cols = [c for c in [CODE, NAME, DATE, PRICE, INVQ, 'فروش', 'باقیمانده', 'وضعیت'] if c]
        return out[cols].copy()

    # ---------------- فروش‌ها ----------------
    df_sales = df_sales.copy()
    SALES_QTY_COL = 'تعداد فروش'

    # تعیین ستون قیمت برای موجودی:
    has_qty = SALES_QTY_COL in df_sales.columns
    has_any_price = ('فی پایه موجودی' in df_sales.columns) or ('قیمت فروش' in df_sales.columns)

    if not has_qty or not has_any_price:
        out = df_inv.copy()
        out['فروش'] = 0
        out['باقیمانده'] = out[INVQ].astype(int)
        out['وضعیت'] = out['باقیمانده'].apply(lambda x: 'تمام شده' if x <= 0 else 'باقی مانده')
        sort_cols = [CODE]
        if DATE:
            sort_cols.append(DATE)
        sort_cols.append(PRICE)
        try:
            out = out.sort_values(sort_cols)
        except Exception:
            pass
        cols = [c for c in [CODE, NAME, DATE, PRICE, INVQ, 'فروش', 'باقیمانده', 'وضعیت'] if c]
        return out[cols].copy()

    # ستون قیمت پایه برای موجودی
    if 'فی پایه موجودی' in df_sales.columns:
        SALES_PRICE_COL = 'فی پایه موجودی'
    else:
        SALES_PRICE_COL = 'قیمت فروش'

    # نرمال‌سازی عددی فروش
    df_sales[SALES_QTY_COL] = pd.to_numeric(df_sales[SALES_QTY_COL],
                                             errors='coerce').fillna(0).astype(int)
    df_sales[SALES_PRICE_COL] = pd.to_numeric(df_sales[SALES_PRICE_COL],
                                               errors='coerce').fillna(0).astype(int)

    # مجموع فروش به ازای (کد کالا، قیمت پایه موجودی)
    sales_agg = (
        df_sales
        .groupby(['کد کالا', SALES_PRICE_COL], as_index=False)[SALES_QTY_COL]
        .sum()
        .rename(columns={
            'کد کالا': CODE,
            SALES_PRICE_COL: PRICE,
            SALES_QTY_COL: 'TOTAL_SOLD'
        })
    )

    # برای دسترسی سریع به مقدار فروش هر (کد، قیمت)
    sales_map = {
        (row[CODE], int(row[PRICE])): int(row['TOTAL_SOLD'])
        for _, row in sales_agg.iterrows()
    }

    # ---------------- اعمال فروش روی لایه‌های موجودی ----------------
    result_rows = []

    # برای FIFO روی تاریخ، اول موجودی را مرتب می‌کنیم
    sort_cols = [CODE]
    if DATE:
        sort_cols.append(DATE)
    sort_cols.append(PRICE)
    df_inv_sorted = df_inv.sort_values(sort_cols).reset_index(drop=True)

    # گروه‌بندی بر اساس (کد، قیمت)
    for (code, price), group in df_inv_sorted.groupby([CODE, PRICE], sort=False):
        total_sold_for_pair = int(sales_map.get((code, int(price)), 0))

        # داخل این (کد، قیمت) روی تاریخ FIFO می‌زنیم
        for _, r in group.iterrows():
            original_qty = int(r[INVQ]) if pd.notnull(r[INVQ]) else 0
            if original_qty < 0:
                original_qty = 0

            if total_sold_for_pair <= 0:
                sold = 0
                remaining = original_qty
            else:
                sold = min(original_qty, total_sold_for_pair)
                remaining = original_qty - sold
                total_sold_for_pair -= sold

            row_out = {
                CODE: r[CODE],
                NAME: r[NAME],
                PRICE: int(r[PRICE]),
                INVQ: original_qty,
                'فروش': int(sold),
                'باقیمانده': int(remaining),
            }
            if DATE:
                row_out[DATE] = r.get(DATE, "")

            result_rows.append(row_out)

    out = pd.DataFrame(result_rows)

    # وضعیت
    out['وضعیت'] = out['باقیمانده'].astype(int).apply(
        lambda x: 'تمام شده' if x <= 0 else 'باقی مانده'
    )

    # مرتب‌سازی نهایی
    sort_cols = ['وضعیت', CODE]
    if DATE:
        sort_cols.append(DATE)
    sort_cols.append(PRICE)
    try:
        out = out.sort_values(sort_cols)
    except Exception:
        pass

    cols = [c for c in [CODE, NAME, DATE, PRICE, INVQ, 'فروش', 'باقیمانده', 'وضعیت'] if c]
    return out[cols].copy()