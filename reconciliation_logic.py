#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import pandas as pd
import datetime as _dt
from persiantools.jdatetime import JalaliDate
from datetime import timedelta

# -------- Helpers --------
_P2E   = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
_AR2FA = str.maketrans({'ك':'ک','ي':'ی','ة':'ه'})

def _strip_rtl_marks(s):
    return (str(s)
            .replace('\u200f','').replace('\u200e','')
            .replace('\u202a','').replace('\u202b','').replace('\u202c','')
            .replace('‌','').replace('‍','').replace('ـ',''))

def _canon_header(s):
    s = _strip_rtl_marks(s).translate(_AR2FA)
    s = re.sub(r'\s+',' ', s).strip()
    return s.casefold()

def smart_convert_date(val):
    if pd.isna(val):
        return pd.NaT
    if isinstance(val, (pd.Timestamp, _dt.datetime, _dt.date)):
        return pd.to_datetime(val)
    s = str(val).strip()
    s = _strip_rtl_marks(s).translate(_P2E).translate(_AR2FA)
    s = s.replace('-', '/').replace('.', '/')
    parts = s.split('/')
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        y, m, d = map(int, parts)
        if 1300 <= y <= 1700:
            try:    return pd.to_datetime(JalaliDate(y, m, d).to_gregorian())
            except: return pd.NaT
        return pd.to_datetime(f"{y:04d}-{m:02d}-{d:02d}", errors='coerce')
    try:
        return pd.to_datetime('1899-12-30') + pd.to_timedelta(float(s), unit='D')
    except:
        return pd.to_datetime(s, errors='coerce')

def _normalize_desc(s):
    if pd.isna(s): return ""
    s = _strip_rtl_marks(s).translate(_AR2FA)
    return re.sub(r'\s+',' ', s).strip()

def _to_jalali_str(dt_val):
    if pd.isna(dt_val): return None
    try: return JalaliDate(pd.to_datetime(dt_val)).strftime("%Y-%m-%d")
    except: return None

def _build_fuzzy_keyword_pattern(keyword):
    kw = _normalize_desc(keyword or "شاپرک")
    letters = [ch for ch in kw if not ch.isspace()] or list("شاپرک")
    sep = r'[\s\-\._]*'
    pattern_fa = sep.join(re.escape(ch) for ch in letters)
    pattern_en = r's'+sep+'h'+sep+'a'+sep+'p'+sep+'a'+sep+'r'+sep+'a'+sep+'k'
    return re.compile(f"(?:{pattern_fa}|{pattern_en})", flags=re.IGNORECASE)

def _guess_col_by_role(df, requested):
    canon_map = {c: _canon_header(c) for c in df.columns}
    req = _canon_header(requested)
    KEYS = {
        'desc':  ['شرح','توضيح','توضیح','بابت','memo','description','desc','details','explanation','narration','note'],
        'date':  ['تاریخ','تاريخ','date','tarikh'],
        'debit': ['بدهکار','بدهي','debit','withdraw','برداشت'],
        'credit':['بستانکار','بستان','credit','deposit','واریز','واريز'],
        'amount':['مبلغ','amount','sum','value','price','fee','figure'],
        'type':  ['نوع','transaction type','type','cat','kind'],
    }
    role = None
    for r, keys in KEYS.items():
        if any(k in req for k in keys): role = r; break
    def _pick(keys):
        for col, canon in canon_map.items():
            if any(k in canon for k in keys): return col
        return None
    if role:
        col = _pick(KEYS[role])
        if col: return col
    # تاریخ حدسی
    try:
        for col in df.columns:
            sample = df[col].dropna().astype(str).head(80)
            if len(sample) >= 10:
                ok = sample.apply(lambda x: pd.notna(smart_convert_date(x))).mean()
                if ok >= 0.6: return col
    except: pass
    # شرح حدسی
    obj_cols = [c for c in df.columns if df[c].dtype == 'object']
    best, best_len = None, -1
    for c in obj_cols:
        s = df[c].dropna().astype(str).head(200).apply(len)
        if not s.empty and s.mean() > best_len:
            best, best_len = c, s.mean()
    return best

def _resolve_col(df, requested, required=True):
    if not requested:
        if required: raise ValueError("نام ستون خالی است.")
        return None
    if requested in df.columns: return requested
    canon_req = _canon_header(requested)
    idx = {}
    for c in df.columns:
        k = _canon_header(c)
        if k not in idx: idx[k] = c
    if canon_req in idx: return idx[canon_req]
    alt = requested.strip()
    if alt in df.columns: return alt
    guess = _guess_col_by_role(df, requested)
    if guess: return guess
    if required:
        raise KeyError(f"ستون «{requested}» در فایل یافت نشد. ستون‌ها: {list(df.columns)}")
    return None

# -------- Pairing helpers (برای حالت تاریخ‌محور) --------
def _pair_same_day_one_to_one(L, l_amt, l_date, R, r_amt, r_date, tol=1.0):
    L = L[[l_amt, l_date]].copy(); L['_idx']=L.index
    R = R[[r_amt, r_date]].copy(); R['_idx']=R.index
    L['_date']=pd.to_datetime(L[l_date], errors='coerce').dt.normalize()
    R['_date']=pd.to_datetime(R[r_date], errors='coerce').dt.normalize()
    L['_amt']=pd.to_numeric(L[l_amt], errors='coerce'); R['_amt']=pd.to_numeric(R[r_amt], errors='coerce')
    L=L.dropna(subset=['_date','_amt']).sort_values(['_date','_amt','_idx'])
    R=R.dropna(subset=['_date','_amt']).sort_values(['_date','_amt','_idx'])
    pairs=[]
    for d in sorted(set(L['_date']).intersection(set(R['_date']))):
        Ll=L[L['_date']==d].reset_index(drop=True)
        Rr=R[R['_date']==d].reset_index(drop=True)
        i=j=0
        while i<len(Ll) and j<len(Rr):
            a=Ll.loc[i,'_amt']; b=Rr.loc[j,'_amt']
            if abs(a-b)<=tol: pairs.append((int(Ll.loc[i,'_idx']), int(Rr.loc[j,'_idx']))); i+=1; j+=1
            elif a<b-tol: i+=1
            else: j+=1
    return pairs

def _pair_within_days_one_to_one(L, l_amt, l_date, R, r_amt, r_date, days=0, tol=1.0):
    if days<=0: return []
    L=L[[l_amt,l_date]].copy(); L['_idx']=L.index
    R=R[[r_amt,r_date]].copy(); R['_idx']=R.index
    L['_date']=pd.to_datetime(L[l_date], errors='coerce').dt.normalize()
    R['_date']=pd.to_datetime(R[r_date], errors='coerce').dt.normalize()
    L['_amt']=pd.to_numeric(L[l_amt], errors='coerce'); R['_amt']=pd.to_numeric(R[r_amt], errors='coerce')
    L=L.dropna(subset=['_date','_amt']).sort_values(['_date','_idx'])
    R=R.dropna(subset=['_date','_amt'])
    used_R=set(); pairs=[]
    for i in range(len(L)):
        a=L.iloc[i]['_amt']; d=L.iloc[i]['_date']
        cand=R.loc[~R['_idx'].isin(used_R)].copy()
        if cand.empty: continue
        cand=cand[(cand['_amt'].sub(a).abs()<=tol)&(cand['_date'].sub(d).abs().dt.days<=days)]
        if cand.empty: continue
        cand['dd']=cand['_date'].sub(d).abs().dt.days
        pick=cand.sort_values(['dd','_idx']).iloc[0]
        pairs.append((int(L.iloc[i]['_idx']), int(pick['_idx'])))
        used_R.add(int(pick['_idx']))
    return pairs

# ================= 1) مغایرت مبلغی =================
def reconcile_with_tolerance(
    input_path, sheet_name, bank_mode,
    date_col, desc_col, debit_col, credit_col, amount_col, type_col,
    yaran_date_col, yaran_desc_col, yaran_debit_col, yaran_credit_col, yaran_tempno_col,
    output_path,
    tolerance=1.0,
    use_date_matching=False,   # ← بدون تیک: False (مچ ساده‌ی فقط مبلغ)
    pair_window_days=0         # ← با تیک: True و این مقدار تعیین‌کنندهٔ پنجرهٔ N روز
):
    # --- load
    dfb_raw = pd.read_excel(input_path, sheet_name=sheet_name)
    dfy_raw = pd.read_excel(input_path, sheet_name='یاران')

    # --- resolve (bank)
    date_col   = _resolve_col(dfb_raw, date_col)
    desc_col   = _resolve_col(dfb_raw, desc_col)
    debit_col  = _resolve_col(dfb_raw, debit_col,  required=(bank_mode=='دو ستون جدا'))
    credit_col = _resolve_col(dfb_raw, credit_col, required=(bank_mode=='دو ستون جدا'))
    amount_col = _resolve_col(dfb_raw, amount_col, required=(bank_mode!='دو ستون جدا'))
    type_col   = _resolve_col(dfb_raw, type_col,   required=(bank_mode!='دو ستون جدا'))

    # --- resolve (yaran)
    yaran_date_col   = _resolve_col(dfy_raw, yaran_date_col)
    yaran_desc_col   = _resolve_col(dfy_raw, yaran_desc_col)
    yaran_debit_col  = _resolve_col(dfy_raw, yaran_debit_col,  required=False)
    yaran_credit_col = _resolve_col(dfy_raw, yaran_credit_col, required=False)
    yaran_tempno_col = _resolve_col(dfy_raw, yaran_tempno_col, required=False)

    # --- normalize Yaran
    dfy = dfy_raw.copy()
    dfy.columns = (dfy.columns.astype(str).map(_strip_rtl_marks).str.replace('ي','ی').str.replace('ك','ک'))
    dfy['تاریخ سند_میلادی'] = pd.to_datetime(dfy[yaran_date_col].apply(smart_convert_date), errors='coerce')
    dfy['تاریخ شمسی یاران'] = dfy[yaran_date_col].astype(str).str.strip()
    dfy['شرح']      = dfy[yaran_desc_col].map(_normalize_desc)
    dfy['بدهکار']   = pd.to_numeric(dfy[yaran_debit_col],  errors='coerce').fillna(0) if yaran_debit_col else 0
    dfy['بستانکار'] = pd.to_numeric(dfy[yaran_credit_col], errors='coerce').fillna(0) if yaran_credit_col else 0
    dfy['شماره موقت'] = (dfy[yaran_tempno_col] if yaran_tempno_col else pd.NA)

    # --- normalize Bank
    if bank_mode == 'دو ستون جدا':
        dfb = dfb_raw.rename(columns={date_col:'تاریخ', desc_col:'شرح', debit_col:'بدهکار', credit_col:'بستانکار'})
        for c in ('بدهکار','بستانکار'):
            dfb[c] = pd.to_numeric(dfb[c].astype(str).str.replace(',',''), errors='coerce').fillna(0)
    else:
        tmp = dfb_raw.copy()
        tmp[type_col] = tmp[type_col].astype(str).str.strip().replace('واريز','واریز').replace('برداشت','برداشت')
        dfb = pd.DataFrame({
            'تاریخ': tmp[date_col],
            'شرح':   tmp[desc_col],
            'بستانکار': tmp.apply(lambda r: float(str(r[amount_col]).replace(',','')) if r[type_col]=='واریز' else 0.0, axis=1),
            'بدهکار':   tmp.apply(lambda r: float(str(r[amount_col]).replace(',','')) if r[type_col]=='برداشت' else 0.0, axis=1),
        })
    if 'شرح' not in dfb.columns:
        raise KeyError(f"ستون «شرح» پس از نگاشت در دیتافریم بانک موجود نیست. ستون‌ها: {list(dfb.columns)}")

    dfb['شرح']   = dfb['شرح'].map(_normalize_desc)
    dfb['تاریخ'] = pd.to_datetime(dfb['تاریخ'].apply(smart_convert_date), errors='coerce')
    dfb['تاریخ شمسی بانک'] = dfb_raw[date_col].astype(str).str.strip()

    # --- Matching paths ---
    mismatches = []

    if not use_date_matching:
        # ===== مسیر بدون تیک: مچ سادهٔ فقط مبلغ (حریصانه) =====
        used_deb_to_cre, used_cre_to_deb = set(), set()

        # بستانکار بانک ↔ بدهکار یاران (فقط مبلغ)
        for _, r in dfb[dfb['بستانکار'] > 0].iterrows():
            matched = False
            for j, y in dfy[dfy['بدهکار'] > 0].iterrows():
                if j in used_deb_to_cre: continue
                if abs(r['بستانکار'] - y['بدهکار']) <= tolerance:
                    used_deb_to_cre.add(j); matched = True; break
            if not matched:
                mismatches.append({
                    "نوع مغایرت": "بستانکار بانک - بدون تطابق در بدهکار یاران",
                    "تاریخ بانک": r['تاریخ شمسی بانک'],
                    "شرح بانک":   r['شرح'],
                    "مبلغ بانک":  r['بستانکار'],
                    "تاریخ یاران": None,
                    "شرح یاران":   None,
                    "مبلغ یاران":  None,
                    "شماره موقت یاران": None
                })

        # بدهکار بانک ↔ بستانکار یاران (فقط مبلغ)
        for _, r in dfb[dfb['بدهکار'] > 0].iterrows():
            matched = False
            for j, y in dfy[dfy['بستانکار'] > 0].iterrows():
                if j in used_cre_to_deb: continue
                if abs(r['बدهکار' if 'बدهکار' in dfb.columns else 'بدهکار'] - y['بستانकार' if 'بستانकार' in dfy.columns else 'بستانکار']) <= tolerance:
                    used_cre_to_deb.add(j); matched = True; break
            if not matched:
                mismatches.append({
                    "نوع مغایرت": "بدهکار بانک - بدون تطابق در بستانکار یاران",
                    "تاریخ بانک": r['تاریخ شمسی بانک'],
                    "شرح بانک":   r['شرح'],
                    "مبلغ بانک":  r['بدهکار'],
                    "تاریخ یاران": None,
                    "شرح یاران":   None,
                    "مبلغ یاران":  None,
                    "شماره موقت یاران": None
                })

        # یاران بی‌جفت
        for j, y in dfy[dfy['بدهکار'] > 0].iterrows():
            if j not in used_deb_to_cre:
                mismatches.append({
                    "نوع مغایرت": "بدهکار یاران - بدون تطبیق در بستانکار بانک",
                    "تاریخ بانک": None, "شرح بانک": None, "مبلغ بانک": None,
                    "تاریخ یاران": y['تاریخ شمسی یاران'],
                    "شرح یاران":   y['شرح'],
                    "مبلغ یاران":  y['بدهکار'],
                    "شماره موقت یاران": y.get('شماره موقت', None)
                })
        for j, y in dfy[dfy['بستانکار'] > 0].iterrows():
            if j not in used_cre_to_deb:
                mismatches.append({
                    "نوع مغایرت": "بستانکار یاران - بدون تطبیق در بدهکار بانک",
                    "تاریخ بانک": None, "شرح بانک": None, "مبلغ بانک": None,
                    "تاریخ یاران": y['تاریخ شمسی یاران'],
                    "شرح یاران":   y['شرح'],
                    "مبلغ یاران":  y['بستانکار'],
                    "شماره موقت یاران": y.get('شماره موقت', None)
                })

    else:
        # ===== مسیر با تیک: همان‌روز + پنجرهٔ Nروزه (یک‌به‌یک) =====
        B_cre = dfb[dfb['بستانکار'] > 0];   Y_deb = dfy[dfy['بدهکار']   > 0]
        pairs1 = _pair_same_day_one_to_one(B_cre,'بستانکار','تاریخ', Y_deb,'بدهکار','تاریخ سند_میلادی', tol=tolerance)
        used_b_cre = set(i for i,_ in pairs1); used_y_deb = set(j for _,j in pairs1)
        if pair_window_days > 0:
            B_cre_left = B_cre.loc[~B_cre.index.isin(used_b_cre)]
            Y_deb_left = Y_deb.loc[~Y_deb.index.isin(used_y_deb)]
            pairs2 = _pair_within_days_one_to_one(B_cre_left,'بستانکار','تاریخ', Y_deb_left,'بدهکار','تاریخ سند_میلادی',
                                                  days=pair_window_days, tol=tolerance)
            used_b_cre |= set(i for i,_ in pairs2); used_y_deb |= set(j for _,j in pairs2)

        B_deb = dfb[dfb['بدهکار']   > 0];   Y_cre = dfy[dfy['بستانکار'] > 0]
        pairs3 = _pair_same_day_one_to_one(B_deb,'بدهکار','تاریخ', Y_cre,'بستانکار','تاریخ سند_میلادی', tol=tolerance)
        used_b_deb = set(i for i,_ in pairs3); used_y_cre = set(j for _,j in pairs3)
        if pair_window_days > 0:
            B_deb_left = B_deb.loc[~B_deb.index.isin(used_b_deb)]
            Y_cre_left = Y_cre.loc[~Y_cre.index.isin(used_y_cre)]
            pairs4 = _pair_within_days_one_to_one(B_deb_left,'بدهکار','تاریخ', Y_cre_left,'بستانکار','تاریخ سند_میلادی',
                                                  days=pair_window_days, tol=tolerance)
            used_b_deb |= set(i for i,_ in pairs4); used_y_cre |= set(j for _,j in pairs4)

        # باقیمانده‌ها = مغایرت
        for idx, r in B_cre.loc[~B_cre.index.isin(used_b_cre)].iterrows():
            mismatches.append({
                "نوع مغایرت": "بستانکار بانک - بدون تطابق در بدهکار یاران",
                "تاریخ بانک": r['تاریخ شمسی بانک'],
                "شرح بانک":   r['شرح'],
                "مبلغ بانک":  r['بستانکار'],
                "تاریخ یاران": None, "شرح یاران": None, "مبلغ یاران": None, "شماره موقت یاران": None
            })
        for idx, r in B_deb.loc[~B_deb.index.isin(used_b_deb)].iterrows():
            mismatches.append({
                "نوع مغایرت": "بدهکار بانک - بدون تطابق در بستانکار یاران",
                "تاریخ بانک": r['تاریخ شمسی بانک'],
                "شرح بانک":   r['شرح'],
                "مبلغ بانک":  r['بدهکار'],
                "تاریخ یاران": None, "شرح یاران": None, "مبلغ یاران": None, "شماره موقت یاران": None
            })
        for idx, y in Y_deb.loc[~Y_deb.index.isin(used_y_deb)].iterrows():
            mismatches.append({
                "نوع مغایرت": "بدهکار یاران - بدون تطبیق در بستانکار بانک",
                "تاریخ بانک": None, "شرح بانک": None, "مبلغ بانک": None,
                "تاریخ یاران": y['تاریخ شمسی یاران'], "شرح یاران": y['شرح'], "مبلغ یاران": y['بدهکار'],
                "شماره موقت یاران": y.get('شماره موقت', None)
            })
        for idx, y in Y_cre.loc[~Y_cre.index.isin(used_y_cre)].iterrows():
            mismatches.append({
                "نوع مغایرت": "بستانکار یاران - بدون تطبیق در بدهکار بانک",
                "تاریخ بانک": None, "شرح بانک": None, "مبلغ بانک": None,
                "تاریخ یاران": y['تاریخ شمسی یاران'], "شرح یاران": y['شرح'], "مبلغ یاران": y['بستانکار'],
                "شماره موقت یاران": y.get('شماره موقت', None)
            })

    # --- Output
    result_df = pd.DataFrame(mismatches)
    summary_df = pd.DataFrame({
        "شرح": [
            "مجموع بستانکار بانک", "مجموع بدهکار یاران", "مغایرت بستانکار بانک - بدهکار یاران",
            "مجموع بدهکار بانک",   "مجموع بستانکار یاران", "مغایرت بدهکار بانک - بستانکار یاران"
        ],
        "مبلغ (ریال)": [
            dfb['بستانکار'].sum(), dfy['بدهکار'].sum(), dfb['بستانکار'].sum() - dfy['بدهکار'].sum(),
            dfb['بدهکار'].sum(),   dfy['بستانکار'].sum(), dfb['بدهکار'].sum() - dfy['بستانکار'].sum()
        ]
    })
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        result_df.to_excel(writer, sheet_name='گزارش مغایرت', index=False)
        summary_df.to_excel(writer, sheet_name='جمع‌بندی کلی', index=False)

# ================= 2) مغایرت شاپرکی =================
def reconcile_shaparak(
    input_path, sheet_name,
    date_col, desc_col, debit_col, credit_col, amount_col, type_col,
    yaran_date_col, yaran_desc_col, yaran_debit_col, yaran_credit_col, yaran_tempno_col,
    output_path,
    keyword="شاپرک", tolerance=1.0, max_delay=7, bank_mode=None
):
    dfb_raw = pd.read_excel(input_path, sheet_name=sheet_name)
    dfy_raw = pd.read_excel(input_path, sheet_name='یاران')

    if bank_mode is None:
        has_sep   = bool(debit_col and credit_col and debit_col in dfb_raw.columns and credit_col in dfb_raw.columns)
        has_typed = bool(amount_col and type_col and amount_col in dfb_raw.columns and type_col in dfb_raw.columns)
        bank_mode = 'دو ستون جدا' if has_sep else ('مبلغ + نوع تراکنش' if has_typed else None)
        if bank_mode is None: raise ValueError("ستون‌های بانک برای تشخیص حالت کافی نیست.")

    # resolve
    date_col   = _resolve_col(dfb_raw, date_col)
    desc_col   = _resolve_col(dfb_raw, desc_col)
    debit_col  = _resolve_col(dfb_raw, debit_col,  required=(bank_mode=='دو ستون جدا'))
    credit_col = _resolve_col(dfb_raw, credit_col, required=(bank_mode=='دو ستون جدا'))
    amount_col = _resolve_col(dfb_raw, amount_col, required=(bank_mode!='دو ستون جدا'))
    type_col   = _resolve_col(dfb_raw, type_col,   required=(bank_mode!='دو ستون جدا'))

    yaran_date_col   = _resolve_col(dfy_raw, yaran_date_col)
    yaran_desc_col   = _resolve_col(dfy_raw, yaran_desc_col)
    yaran_debit_col  = _resolve_col(dfy_raw, yaran_debit_col,  required=False)
    yaran_credit_col = _resolve_col(dfy_raw, yaran_credit_col, required=False)
    yaran_tempno_col = _resolve_col(dfy_raw, yaran_tempno_col, required=False)

    # normalize Yaran
    dfy = dfy_raw.copy()
    dfy.columns = (dfy.columns.astype(str).map(_strip_rtl_marks).str.replace('ي','ی').str.replace('ك','ک'))
    dfy['تاریخ سند_میلادی'] = pd.to_datetime(dfy[yaran_date_col].apply(smart_convert_date), errors='coerce').dt.normalize()
    dfy['تاریخ شمسی یاران']  = dfy[yaran_date_col].astype(str).str.strip()
    dfy['شرح']      = dfy[yaran_desc_col].map(_normalize_desc)
    dfy['بدهکار']   = pd.to_numeric(dfy[yaran_debit_col],  errors='coerce').fillna(0) if yaran_debit_col else 0
    dfy['بستانکار'] = pd.to_numeric(dfy[yaran_credit_col], errors='coerce').fillna(0) if yaran_credit_col else 0
    dfy['شماره موقت'] = (dfy[yaran_tempno_col] if yaran_tempno_col else pd.NA)

    # normalize Bank
    if bank_mode == 'دو ستون جدا':
        dfb = dfb_raw.rename(columns={date_col:'تاریخ', desc_col:'شرح', debit_col:'بدهکار', credit_col:'بستانکار'})
        for c in ('بدهکار','بستانکار'):
            dfb[c] = pd.to_numeric(dfb[c].astype(str).str.replace(',',''), errors='coerce').fillna(0)
    else:
        tmp = dfb_raw.copy()
        tmp[type_col] = tmp[type_col].astype(str).str.strip().replace('واريز','واریز').replace('برداشت','برداشت')
        dfb = pd.DataFrame({
            'تاریخ': tmp[date_col],
            'شرح':   tmp[desc_col],
            'بستانکار': tmp.apply(lambda r: float(str(r[amount_col]).replace(',','')) if r[type_col]=='واریز' else 0.0, axis=1),
            'بدهکار':   tmp.apply(lambda r: float(str(r[amount_col]).replace(',','')) if r[type_col]=='برداشت' else 0.0, axis=1),
        })
    if 'شرح' not in dfb.columns:
        raise KeyError(f"ستون «شرح» پس از نگاشت در دیتافریم بانک موجود نیست. ستون‌ها: {list(dfb.columns)}")

    dfb['شرح']   = dfb['شرح'].map(_normalize_desc)
    dfb['تاریخ'] = pd.to_datetime(dfb['تاریخ'].apply(smart_convert_date), errors='coerce').dt.normalize()

    # fuzzy shaparak, day>=2
    pattern = _build_fuzzy_keyword_pattern(keyword)
    shp = dfb[(dfb['بستانکار'] > 0) & (dfb['شرح'].str.contains(pattern, na=False)) & dfb['تاریخ'].dt.day.ge(2)].copy()
    if shp.empty:
        raise RuntimeError("هیچ رکورد شاپرکی بعد از روز اول ماه پیدا نشد.")

    mism_s, used_b, used_y = [], set(), set()
    for day in sorted(shp['تاریخ'].unique()):
        bank_sum  = shp[shp['تاریخ']==day]['بستانکار'].sum()
        yar_day   = day - timedelta(days=1)
        yaran_sum = dfy[dfy['تاریخ سند_میلادی']==yar_day]['بدهکار'].sum()
        diff_val  = bank_sum - yaran_sum
        if abs(diff_val) > tolerance:
            mism_s.append({
                "تاریخ بانک":  _to_jalali_str(day),
                "مبلغ بستانکار بانک": bank_sum,
                "تاریخ یاران": _to_jalali_str(yar_day),
                "مبلغ بدهکار یاران": yaran_sum,
                "اختلاف (ریال)": diff_val,
            })
        used_b |= set(shp[shp['تاریخ']==day].index)
        used_y |= set(dfy[(dfy['تاریخ سند_میلادی']==yar_day) & (dfy['بدهکار']>0)].index)

    dfb_rem = dfb.drop(index=used_b, errors='ignore').copy()
    dfy_rem = dfy.drop(index=used_y, errors='ignore').copy()

    dfy_deb = dfy_rem[dfy_rem['بدهکار']   > 0].sort_values(['تاریخ سند_میلادی','بدهکار']).copy()
    dfy_cre = dfy_rem[dfy_rem['بستانکار'] > 0].sort_values(['تاریخ سند_میلادی','بستانکار']).copy()

    mism_r = []
    for idx_b, row_b in dfb_rem[dfb_rem['بستانکار'] > 0].iterrows():
        amt, dt = row_b['بستانکار'], row_b['تاریخ']
        cand = dfy_deb[(dfy_deb['بدهکار'].between(amt - tolerance, amt + tolerance)) &
                       (dfy_deb['تاریخ سند_میلادی'] == dt)]
        if not cand.empty:
            y_idx = cand.index[0]
            dfb_rem.drop(index=idx_b, inplace=True); dfy_deb.drop(index=y_idx, inplace=True)
        else:
            mism_r.append({
                "نوع مغایرت": "بستانکار بانک - بدون تطبیق در بدهکار یاران",
                "تاریخ بانک": _to_jalali_str(dt), "شرح بانک": row_b['شرح'], "مبلغ بانک": amt,
                "تاریخ یاران": None, "شرح یاران": None, "مبلغ یاران": None
            })

    for idx_b, row_b in dfb_rem[dfb_rem['بدهکار'] > 0].iterrows():
        amt, dt = row_b['بدهکار'], row_b['تاریخ']
        low, high = dt, dt + timedelta(days=max_delay)
        cand = dfy_cre[(dfy_cre['بستانکار'].between(amt - tolerance, amt + tolerance)) &
                       (dfy_cre['تاریخ سند_میلادی'].between(low, high))]
        if not cand.empty:
            y_idx = cand.index[0]
            dfb_rem.drop(index=idx_b, inplace=True); dfy_cre.drop(index=y_idx, inplace=True)
        else:
            mism_r.append({
                "نوع مغایرت": "بدهکار بانک - بدون تطبیق در بستانکار یاران",
                "تاریخ بانک": _to_jalali_str(dt), "شرح بانک": row_b['شرح'], "مبلغ بانک": amt,
                "تاریخ یاران": None, "شرح یاران": None, "مبلغ یاران": None
            })

    with pd.ExcelWriter(output_path, engine='openpyxl') as w:
        pd.DataFrame(mism_s).to_excel(w, sheet_name='مغایرت شاپرکی', index=False)
        pd.DataFrame(mism_r).to_excel(w, sheet_name='مغایرت مبلغی باقیمانده', index=False)

# ==== Logging + Header Normalization Wrappers (safe syntax) ====
import logging, os, re
from logging.handlers import RotatingFileHandler

_DEF_LOGGER_NAME = "reconciliation"
_LOGGER = None

def _ensure_logger(log_path=None, level=logging.DEBUG):
    global _LOGGER
    if _LOGGER and log_path is None:
        return _LOGGER
    logger = logging.getLogger(_DEF_LOGGER_NAME)
    logger.setLevel(level)
    # redirect handlers if new path provided
    if log_path:
        for h in list(logger.handlers):
            logger.removeHandler(h)
    if not logger.handlers:
        if not log_path:
            log_path = os.path.abspath(os.path.join(os.getcwd(), "reconciliation.log"))
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        fh = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3, encoding='utf-8')
        fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
        fh.setLevel(level)
        logger.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
        sh.setLevel(logging.INFO)
        logger.addHandler(sh)
    _LOGGER = logger
    return logger

# ---- Helpers ----
_AR2FA_MAP = str.maketrans({
    '\u064a': '\u06cc',  # ي -> ی
    '\u0649': '\u06cc',  # ى -> ی
    '\u0643': '\u06a9',  # ك -> ک
    '\u0629': '\u0647',  # ة -> ه
    '\u0623': '\u0627',  # أ -> ا
    '\u0625': '\u0627',  # إ -> ا
    '\u0622': '\u0627',  # آ -> ا (approx)
    '\u06c0': '\u0647',  # ۀ -> ه
})
_DIG_MAP = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')

def norm_text(s):
    if s is None:
        return ''
    s = str(s)
    s = s.replace('\ufeff','').replace('\u200f','').replace('\u200e','').replace('\u202a','').replace('\u202b','').replace('\u202c','')
    s = s.replace('\u200c', ' ')
    s = s.translate(_AR2FA_MAP).translate(_DIG_MAP)
    s = re.sub(r'\s+', ' ', s).strip()
    s = s.replace('تاريخ', 'تاریخ').replace('بدهكار', 'بدهکار').replace('بستانكار', 'بستانکار')
    s = s.replace('شرح سند', 'شرح').replace('شرح ', 'شرح').replace(' شرح', 'شرح')
    return s

def norm_cols(df, logger, tag):
    orig = list(map(str, df.columns))
    new = [norm_text(c) for c in df.columns]
    mapping = {o: n for o, n in zip(orig, new) if o != n}
    if mapping:
        logger.info("نرمال‌سازی هدرهای %s: %s", tag, mapping)
    df = df.rename(columns=mapping)
    return df

def resolve_col(df, requested, logger, tag):
    req = norm_text(requested)
    cols_norm = [norm_text(c) for c in df.columns]
    # exact
    for cn, raw in zip(cols_norm, df.columns):
        if cn == req:
            return raw
    # whitespace-insensitive
    req2 = req.replace(' ', '')
    for cn, raw in zip(cols_norm, df.columns):
        if cn.replace(' ', '') == req2:
            logger.warning("ستون '%s' با تغییر فاصله‌ها در %s یافت شد -> '%s'", requested, tag, raw)
            return raw
    # partial
    for cn, raw in zip(cols_norm, df.columns):
        if req in cn or cn in req:
            logger.warning("ستون '%s' به صورت تقریبی در %s یافت شد -> '%s'", requested, tag, raw)
            return raw
    logger.error("یافت نشد: ستون '%s' در %s پس از نرمال‌سازی؛ ستون‌ها: %s", requested, tag, list(df.columns))
    return requested

def _date_diag(df, col, name, logger):
    try:
        raw = df[col]
    except Exception as e:
        logger.error("ستون %s در دیتافریم %s یافت نشد: %s", col, name, e)
        return
    try:
        import pandas as pd
        # fallback smart convert
        def smart_convert_date(x):
            from datetime import datetime
            xs = str(x)
            xs = norm_text(xs)
            for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    return datetime.strptime(xs, fmt)
                except Exception:
                    pass
            return pd.NaT
        conv = raw.apply(smart_convert_date)
        nat_mask = conv.isna()
        if nat_mask.any():
            bad = raw[nat_mask].astype(str).str.strip().value_counts().head(8).to_dict()
            logger.warning("در %s تعداد تاریخ نامعتبر: %d (نمونه‌ها: %s)", name, int(nat_mask.sum()), bad)
        else:
            logger.info("تبدیل تاریخ‌ها در %s بدون مشکل.", name)
    except Exception as e:
        logger.exception("اشکال در بررسی تبدیل تاریخِ %s: %s", name, e)

# Preserve originals
_reconcile_with_tolerance_orig = reconcile_with_tolerance
_reconcile_shaparak_orig = reconcile_shaparak

def reconcile_with_tolerance(*, input_path, sheet_name, bank_mode,
    date_col, desc_col, debit_col, credit_col, amount_col, type_col,
    yaran_date_col, yaran_desc_col, yaran_debit_col, yaran_credit_col, yaran_tempno_col,
    output_path, tolerance=1.0, use_date_matching=False, pair_window_days=0, log_path=None):
    logger = _ensure_logger(log_path or (str(output_path) + ".log"))
    logger.info("شروع reconcile_with_tolerance | فایل=%s | شیت بانک=%s | حالت=%s | پنجره‌روز=%s | فقط مبلغ=%s",
                input_path, sheet_name, bank_mode, pair_window_days, not use_date_matching)
    logger.info("ستون‌ها | بانک: تاریخ=%s شرح=%s بدهکار=%s بستانکار=%s مبلغ=%s نوع=%s | یاران: تاریخ=%s شرح=%s بدهکار=%s بستانکار=%s موقت=%s",
                date_col, desc_col, debit_col, credit_col, amount_col, type_col,
                yaran_date_col, yaran_desc_col, yaran_debit_col, yaran_credit_col, yaran_tempno_col)

    # defaults
    date_col_eff, desc_col_eff, debit_col_eff, credit_col_eff, amount_col_eff, type_col_eff = \
        date_col, desc_col, debit_col, credit_col, amount_col, type_col
    yaran_date_col_eff, yaran_desc_col_eff, yaran_debit_col_eff, yaran_credit_col_eff, yaran_tempno_col_eff = \
        yaran_date_col, yaran_desc_col, yaran_debit_col, yaran_credit_col, yaran_tempno_col
    input_to_use = input_path

    # Sheet existence + normalization
    try:
        import pandas as pd
        xls = pd.ExcelFile(input_path)
        sheets = xls.sheet_names
        if sheet_name not in sheets:
            logger.warning("شیت بانک '%s' در فایل وجود ندارد. شیت‌ها: %s", sheet_name, sheets)
        if 'یاران' not in sheets:
            logger.warning("شیت 'یاران' در فایل وجود ندارد. شیت‌ها: %s", sheets)

        dfb_raw = pd.read_excel(xls, sheet_name=sheet_name)
        dfy_raw = pd.read_excel(xls, sheet_name='یاران')
        dfb = norm_cols(dfb_raw, logger, 'بانک')
        dfy = norm_cols(dfy_raw, logger, 'یاران')

        # resolve
        date_col_eff   = resolve_col(dfb, date_col, logger, 'بانک') if date_col else ''
        desc_col_eff   = resolve_col(dfb, desc_col, logger, 'بانک') if desc_col else ''
        debit_col_eff  = resolve_col(dfb, debit_col, logger, 'بانک') if debit_col else ''
        credit_col_eff = resolve_col(dfb, credit_col, logger, 'بانک') if credit_col else ''
        amount_col_eff = resolve_col(dfb, amount_col, logger, 'بانک') if amount_col else ''
        type_col_eff   = resolve_col(dfb, type_col, logger, 'بانک') if type_col else ''

        yaran_date_col_eff   = resolve_col(dfy, yaran_date_col, logger, 'یاران') if yaran_date_col else ''
        yaran_desc_col_eff   = resolve_col(dfy, yaran_desc_col, logger, 'یاران') if yaran_desc_col else ''
        yaran_debit_col_eff  = resolve_col(dfy, yaran_debit_col, logger, 'یاران') if yaran_debit_col else ''
        yaran_credit_col_eff = resolve_col(dfy, yaran_credit_col, logger, 'یاران') if yaran_credit_col else ''
        yaran_tempno_col_eff = resolve_col(dfy, yaran_tempno_col, logger, 'یاران') if yaran_tempno_col else ''

        # write normalized workbook
        tmp_dir = os.path.dirname(os.path.abspath(output_path)) or os.getcwd()
        input_to_use = os.path.join(tmp_dir, "._recon_norm.xlsx")
        with pd.ExcelWriter(input_to_use, engine='openpyxl') as writer:
            dfb.to_excel(writer, index=False, sheet_name=sheet_name)
            dfy.to_excel(writer, index=False, sheet_name='یاران')
        logger.info("ورک‌بوک نرمال‌شده ساخته شد: %s", input_to_use)
    except Exception as e:
        logger.warning("نرمال‌سازی/خواندن شیت‌ها انجام نشد: %s", e)

    # Run original
    try:
        res = _reconcile_with_tolerance_orig(
            input_path=input_to_use, sheet_name=sheet_name, bank_mode=bank_mode,
            date_col=date_col_eff, desc_col=desc_col_eff, debit_col=debit_col_eff, credit_col=credit_col_eff,
            amount_col=amount_col_eff, type_col=type_col_eff,
            yaran_date_col=yaran_date_col_eff, yaran_desc_col=yaran_desc_col_eff,
            yaran_debit_col=yaran_debit_col_eff, yaran_credit_col=yaran_credit_col_eff, yaran_tempno_col=yaran_tempno_col_eff,
            output_path=output_path, tolerance=tolerance,
            use_date_matching=use_date_matching, pair_window_days=pair_window_days
        )
        logger.info("پایان موفق reconcile_with_tolerance. خروجی ذخیره شد: %s", output_path)
        return res
    except Exception as e:
        logger.error("شکست در reconcile_with_tolerance: %s", e)
        try:
            import pandas as pd
            dfb_raw = pd.read_excel(input_path, sheet_name=sheet_name)
            dfy_raw = pd.read_excel(input_path, sheet_name='یاران')
            _date_diag(dfb_raw, date_col, "تاریخ بانک (خام)", logger)
            _date_diag(dfy_raw, yaran_date_col, "تاریخ یاران (خام)", logger)
            logger.info("ستون‌های بانک: %s", list(map(str, dfb_raw.columns)))
            logger.info("ستون‌های یاران: %s", list(map(str, dfy_raw.columns)))
        except Exception as ee:
            logger.warning("نتوانستم برای خطا، داده‌ها را تحلیل کنم: %s", ee)
        logger.exception("Traceback:")
        raise

def reconcile_shaparak(*, input_path, sheet_name,
    date_col, desc_col, debit_col, credit_col, amount_col, type_col,
    yaran_date_col, yaran_desc_col, yaran_debit_col, yaran_credit_col, yaran_tempno_col,
    output_path, keyword="شاپرک", tolerance=1.0, max_delay=7, bank_mode=None, log_path=None):
    logger = _ensure_logger(log_path or (str(output_path) + ".log"))
    logger.info("شروع reconcile_shaparak | فایل=%s | شیت بانک=%s | کلمه=%s | max_delay=%s", input_path, sheet_name, keyword, max_delay)
    logger.info("ستون‌ها | بانک: تاریخ=%s شرح=%s بدهکار=%s بستانکار=%s مبلغ=%s نوع=%s | یاران: تاریخ=%s شرح=%s بدهکار=%s بستانکار=%s موقت=%s",
                date_col, desc_col, debit_col, credit_col, amount_col, type_col,
                yaran_date_col, yaran_desc_col, yaran_debit_col, yaran_credit_col, yaran_tempno_col)

    # defaults
    date_col_eff, desc_col_eff, debit_col_eff, credit_col_eff, amount_col_eff, type_col_eff = \
        date_col, desc_col, debit_col, credit_col, amount_col, type_col
    yaran_date_col_eff, yaran_desc_col_eff, yaran_debit_col_eff, yaran_credit_col_eff, yaran_tempno_col_eff = \
        yaran_date_col, yaran_desc_col, yaran_debit_col, yaran_credit_col, yaran_tempno_col
    input_to_use = input_path

    try:
        import pandas as pd
        xls = pd.ExcelFile(input_path)
        sheets = xls.sheet_names
        if sheet_name not in sheets:
            logger.warning("شیت بانک '%s' در فایل وجود ندارد. شیت‌ها: %s", sheet_name, sheets)
        if 'یاران' not in sheets:
            logger.warning("شیت 'یاران' در فایل وجود ندارد. شیت‌ها: %s", sheets)

        dfb_raw = pd.read_excel(xls, sheet_name=sheet_name)
        dfy_raw = pd.read_excel(xls, sheet_name='یاران')
        dfb = norm_cols(dfb_raw, logger, 'بانک')
        dfy = norm_cols(dfy_raw, logger, 'یاران')

        date_col_eff   = resolve_col(dfb, date_col, logger, 'بانک') if date_col else ''
        desc_col_eff   = resolve_col(dfb, desc_col, logger, 'بانک') if desc_col else ''
        debit_col_eff  = resolve_col(dfb, debit_col, logger, 'بانک') if debit_col else ''
        credit_col_eff = resolve_col(dfb, credit_col, logger, 'بانک') if credit_col else ''
        amount_col_eff = resolve_col(dfb, amount_col, logger, 'بانک') if amount_col else ''
        type_col_eff   = resolve_col(dfb, type_col, logger, 'بانک') if type_col else ''

        yaran_date_col_eff   = resolve_col(dfy, yaran_date_col, logger, 'یاران') if yaran_date_col else ''
        yaran_desc_col_eff   = resolve_col(dfy, yaran_desc_col, logger, 'یاران') if yaran_desc_col else ''
        yaran_debit_col_eff  = resolve_col(dfy, yaran_debit_col, logger, 'یاران') if yaran_debit_col else ''
        yaran_credit_col_eff = resolve_col(dfy, yaran_credit_col, logger, 'یاران') if yaran_credit_col else ''
        yaran_tempno_col_eff = resolve_col(dfy, yaran_tempno_col, logger, 'یاران') if yaran_tempno_col else ''

        tmp_dir = os.path.dirname(os.path.abspath(output_path)) or os.getcwd()
        input_to_use = os.path.join(tmp_dir, "._recon_norm.xlsx")
        with pd.ExcelWriter(input_to_use, engine='openpyxl') as writer:
            dfb.to_excel(writer, index=False, sheet_name=sheet_name)
            dfy.to_excel(writer, index=False, sheet_name='یاران')
        logger.info("ورک‌بوک نرمال‌شده ساخته شد: %s", input_to_use)
    except Exception as e:
        logger.warning("نرمال‌سازی/خواندن شیت‌ها انجام نشد: %s", e)

    try:
        res = _reconcile_shaparak_orig(
            input_path=input_to_use, sheet_name=sheet_name,
            date_col=date_col_eff, desc_col=desc_col_eff, debit_col=debit_col_eff, credit_col=credit_col_eff,
            amount_col=amount_col_eff, type_col=type_col_eff,
            yaran_date_col=yaran_date_col_eff, yaran_desc_col=yaran_desc_col_eff,
            yaran_debit_col=yaran_debit_col_eff, yaran_credit_col=yaran_credit_col_eff, yaran_tempno_col=yaran_tempno_col_eff,
            output_path=output_path, keyword=keyword, tolerance=tolerance, max_delay=max_delay, bank_mode=bank_mode
        )
        logger.info("پایان موفق reconcile_shaparak. خروجی ذخیره شد: %s", output_path)
        return res
    except Exception as e:
        logger.error("شکست در reconcile_shaparak: %s", e)
        try:
            import pandas as pd
            dfb_raw = pd.read_excel(input_path, sheet_name=sheet_name)
            dfy_raw = pd.read_excel(input_path, sheet_name='یاران')
            _date_diag(dfb_raw, date_col, "تاریخ بانک (خام)", logger)
            _date_diag(dfy_raw, yaran_date_col, "تاریخ یاران (خام)", logger)
            logger.info("ستون‌های بانک: %s", list(map(str, dfb_raw.columns)))
            logger.info("ستون‌های یاران: %s", list(map(str, dfy_raw.columns)))
        except Exception as ee:
            logger.warning("نتوانستم برای خطا، داده‌ها را تحلیل کنم: %s", ee)
        logger.exception("Traceback:")
        raise