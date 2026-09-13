ذ # ffasli_logic.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import pandas as pd

# --------------------- توابع تاریخ جلالی ---------------------
def is_leap_jalali(year):
    return year % 33 in [1,5,9,13,17,22,26,30]

def next_day_jalali(date_str):
    y, m, d = map(int, date_str.split('/'))
    ml = 31 if m<=6 else (30 if m<=11 else (30 if is_leap_jalali(y) else 29))
    if d < ml:
        d += 1
    else:
        d = 1
        if m == 12:
            m, y = 1, y + 1
        else:
            m += 1
    return f"{y:04d}/{m:02d}/{d:02d}"

def add_days_jalali(date_str, days):
    for _ in range(int(days)):
        date_str = next_day_jalali(date_str)
    return date_str

def days_between(start, end):
    d, cnt = start, 0
    while d != end and cnt < 500:
        d = next_day_jalali(d)
        cnt += 1
    return cnt

def get_season_and_end(date_str):
    y, m, _ = map(int, date_str.split('/'))
    if m in [1,2,3]:  return 'بهار',    f"{y:04d}/03/31"
    if m in [4,5,6]:  return 'تابستان', f"{y:04d}/06/31"
    if m in [7,8,9]:  return 'پاییز',   f"{y:04d}/09/30"
    de = 30 if is_leap_jalali(y) else 29
    return 'زمستان',  f"{y:04d}/12/{de:02d}"

# ----------------- تولید فاکتور فروش (عین منطق نسخه Tkinter) -----------------
def generate_sales(
    df_inv: pd.DataFrame,
    df_cust: pd.DataFrame,
    inv_cols: dict,
    cust_cols: dict,
    start_inv_no: int,
    start_doc_id: int,
    min_total: int,
    max_total: int
) -> pd.DataFrame:
    # آماده‌سازی لیست محصولات
    products = []
    for _, r in df_inv.iterrows():
        start = next_day_jalali(str(r[inv_cols['date']]))
        season, season_end = get_season_and_end(start)
        products.append({
            'code':       r[inv_cols['code']],
            'name':       r[inv_cols['name']],
            'price':      r[inv_cols['price']],
            'inv':        int(r[inv_cols['quantity']]),
            'start':      start,
            'season':     season,
            'season_end': season_end
        })

    invoices = []

    # ۱) فروش داخل هر فصل
    for season in ['بهار','تابستان','پاییز','زمستان']:
        prod_s = [p for p in products if p['season'] == season and p['inv'] > 0]
        while any(p['inv'] > 0 for p in prod_s):
            cust = df_cust.sample().iloc[0]
            avail = sum(1 for p in prod_s if p['inv'] > 0)
            distinct = random.randint(2, min(6, avail)) if avail >= 2 else avail

            items, total, tries = [], 0, 0
            while (len(items) < distinct or total < min_total) and tries < 2000:
                if len(items) < distinct:
                    used_codes = {it['prod']['code'] for it in items}
                    pool = [p for p in prod_s if p['inv'] > 0 and p['code'] not in used_codes]
                else:
                    pool = [p for p in prod_s if p['inv'] > 0]

                pool = [p for p in pool if p['price'] <= (max_total - total)]
                if not pool:
                    break

                p = random.choice(pool)
                max_q = min(p['inv'], int((max_total - total) / p['price']))  # همون cast نسخه Tkinter
                if max_q < 1:
                    tries += 1
                    continue

                q = random.randint(1, max_q)
                items.append({'prod': p, 'qty': q, 'line_total': q * p['price']})
                total += q * p['price']
                p['inv'] -= q
                tries += 1

            # تضمین حداقل مبلغ (ممکنه از سقف بگذره) — همان منطق
            if total < min_total:
                for p in prod_s:
                    if p['inv'] > 0:
                        q = p['inv']
                        items.append({'prod': p, 'qty': q, 'line_total': q * p['price']})
                        total += q * p['price']
                        p['inv'] = 0

            # تاریخ فاکتور داخل بازه‌ای تا انتهای فصل
            earliest   = max(it['prod']['start'] for it in items)
            season_end = items[0]['prod']['season_end']
            max_d      = days_between(earliest, season_end)
            window     = min(random.randint(23, 26), max_d)
            inv_date   = add_days_jalali(earliest, random.randint(0, window))

            invoices.append({
                'cust_code': cust[cust_cols['code']],
                'cust_name': cust[cust_cols['name']],
                'date':      inv_date,
                'season':    season,
                'items':     items
            })

    # ۲) تخلیه نهایی موجودی (خارج از فصل)
    leftovers = [p for p in products if p['inv'] > 0]
    while any(p['inv'] > 0 for p in leftovers):
        cust = df_cust.sample().iloc[0]
        items, total = [], 0
        for p in leftovers:
            if p['inv'] > 0:
                max_q = min(p['inv'], int((max_total - total) / p['price']))
                if max_q > 0:
                    items.append({'prod': p, 'qty': max_q, 'line_total': max_q * p['price']})
                    total += max_q * p['price']
                    p['inv'] -= max_q
        if not items:
            break
        last_date = invoices[-1]['date']
        inv_date  = next_day_jalali(last_date)
        invoices.append({
            'cust_code': cust[cust_cols['code']],
            'cust_name': cust[cust_cols['name']],
            'date':      inv_date,
            'season':    'تخلیه‌نهایی',
            'items':     items
        })

    # شماره‌گذاری و تخت‌کردن خروجی
    invoices.sort(key=lambda x: x['date'])
    for idx, inv in enumerate(invoices, start=start_inv_no):
        inv['inv_no'] = idx
        inv['doc_id'] = start_doc_id + (idx - start_inv_no)

    rows = []
    for inv in invoices:
        for it in inv['items']:
            p = it['prod']
            rows.append({
                'شماره فاکتور': inv['inv_no'],
                'شناسه سند':    inv['doc_id'],
                'تاریخ':        inv['date'],
                'فصل':          inv['season'],
                'کد مشتری':     inv['cust_code'],
                'نام مشتری':    inv['cust_name'],
                'کد کالا':      p['code'],
                'نام کالا':     p['name'],
                'قیمت فروش':    p['price'],
                'تعداد فروش':   it['qty'],
                'جمع کل':       it['line_total']
            })
    return pd.DataFrame(rows)