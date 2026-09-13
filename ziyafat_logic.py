# ziyafat_logic.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json
import pandas as pd
import numpy as np

# ---------------- State for last used ID/Serial ----------------
STATE_FILE = os.path.join(os.path.dirname(__file__), "ziyafat_state.json")
DEFAULT_START_ID = 1
DEFAULT_START_SERIAL = 1
try:
    from core.state import get_state, set_state, migrate_json_file_to_state
    migrate_json_file_to_state(STATE_FILE, "ziyafat_state")
except Exception:
    get_state = None; set_state = None

# کدهای معاف از مالیات
TAX_EXEMPT_CODES = {11000, 2000, 2020, 2021, 2022, 2003}

def load_next_defaults(default_id: int = DEFAULT_START_ID,
                       default_serial: int = DEFAULT_START_SERIAL) -> tuple[int, int]:
    """
    مقدار پیش‌فرض برای «شروع شناسه/سریال» را برمی‌گرداند:
      next_id     = max(default_id,  last_id + 1)
      next_serial = max(default_serial, last_serial + 1)
    اگر فایل state نباشد، همان defaultها برگردانده می‌شوند.
    """
    try:
        if get_state is not None:
            st = get_state("ziyafat_state") or {}
        else:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                st = json.load(f)
        last_id = int(st.get("last_id", default_id - 1))
        last_serial = int(st.get("last_serial", default_serial - 1))
        return max(default_id, last_id + 1), max(default_serial, last_serial + 1)
    except Exception:
        return default_id, default_serial

def save_last_used(df_out: pd.DataFrame) -> None:
    """
    حداکثر «شناسه» و «شماره سریال» تولیدشده در df_out را ذخیره می‌کند
    تا سری بعد +۱ به‌عنوان پیش‌فرض استفاده شود.
    """
    try:
        last_id = int(pd.to_numeric(df_out["شناسه"], errors="coerce").max() or 0)
        last_serial = int(pd.to_numeric(df_out["شماره سریال"], errors="coerce").max() or 0)
        st = {"last_id": last_id, "last_serial": last_serial}
        if set_state is not None:
            set_state("ziyafat_state", st)
        else:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(st, f, ensure_ascii=False)
    except Exception as e:
        # عمداً سایلنت؛ نذار خروجی خراب شود
        print("[WARN] cannot write state:", e)

# ---------------- Core logic ----------------
def standardize_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    یکسان‌سازی ستون‌های ورودی:
      - اصلاح نام ستون‌ها (عربی → فارسی)
      - حذف ستون‌های تکراری
    """
    df = df.copy()
    df.columns = (
        df.columns
          .str.strip()
          .str.replace('ي', 'ی')
          .str.replace('ك', 'ک')
    )
    df.rename(columns={
        "قيمت": "قیمت",
        "تخفيف": "تخفیف",
        "ماليات": "مالیات",
        "اضافات": "اضافات",
    }, inplace=True)
    # ستون «شماره پیوست»
    attach = [c for c in df.columns if "پیوست" in c]
    if attach:
        df.rename(columns={attach[0]: "شماره پیوست"}, inplace=True)
    # ستون «توضیحات فاکتور»
    desc = [c for c in df.columns if "توضیح" in c or "توضیحات" in c]
    if desc:
        df.rename(columns={desc[0]: "توضیحات فاکتور"}, inplace=True)
    # حذف ستون‌های تکراری
    return df.loc[:, ~df.columns.duplicated()]

def process_ziyafat(
    file_saloon: str,
    file_biroonbar: str,
    file_moadele: str,
    start_id: int,
    start_serial: int,
    output_path: str
) -> None:
    """
    منطق «تبدیل فایل‌های فروش رستوران» (صفحهٔ ضیافت).
    خروجی: یک اکسل با دو شیت «خروجی» و «محاسبه».
    نکته: بعد از خروجی، آخرین شناسه/سریال در STATE_FILE ذخیره می‌شود.
    """
    # 1) خواندن و استانداردسازی ورودی‌ها
    df_sal = standardize_df(pd.read_excel(file_saloon))
    df_bi  = standardize_df(pd.read_excel(file_biroonbar))
    df_sal["نوع فروش"] = "سالن"
    df_bi ["نوع فروش"] = "بیرون‌بر"

    df_all = pd.concat([df_sal, df_bi], ignore_index=True)
    df_all.columns = df_all.columns.str.strip()

    # ستون‌های حیاتی
    if "تاریخ" not in df_all.columns:
        raise ValueError("ستون «تاریخ» در فایل‌های ورودی یافت نشد.")
    if "کد کالا" not in df_all.columns:
        raise ValueError("ستون «کد کالا» در فایل‌های ورودی یافت نشد.")

    # مرتب‌سازی زمانی
    df_all.sort_values("تاریخ", inplace=True)
    df_all.reset_index(drop=True, inplace=True)

    # 6111 → 11000
    df_all.loc[df_all["کد کالا"] == 6111, "کد کالا"] = 11000

    # 2) معادل‌سازی مشتری
    df_map = pd.read_excel(file_moadele)
    df_map.columns = df_map.columns.str.strip()
    if not {"کد مشتری", "کد جدید"}.issubset(df_map.columns):
        raise ValueError("ستون‌های «کد مشتری» یا «کد جدید» در فایل معادل‌سازی یافت نشد.")
    df_map["کد مشتری"] = df_map["کد مشتری"].astype(int)
    df_map["کد جدید"]   = df_map["کد جدید"].astype(int)
    customer_map = dict(zip(df_map["کد مشتری"], df_map["کد جدید"]))

    # 3) ستون‌های لازم برای ساخت خروجی
    required = {
        "شماره فاکتور", "کد مشتری", "نام مشتری",
        "تعداد", "قیمت", "شماره پیوست", "توضیحات فاکتور", "نام کالا"
    }
    missing = required - set(df_all.columns)
    if missing:
        raise ValueError(f"ستون‌های {missing} در داده‌های ورودی یافت نشد.")

    # 4) ساخت df_out
    df_out = pd.DataFrame({
        "شماره فاکتور": df_all["شماره فاکتور"],
        "تاریخ":        df_all["تاریخ"],
        "کد مشتری":     df_all["کد مشتری"].map(customer_map).fillna(2000).astype(int),
        "نام مشتری":    df_all["نام مشتری"].where(
                             df_all["کد مشتری"].map(customer_map).notna(),
                             "مشتری عمومی"
                         ),
        "توضیحات":      df_all["شماره پیوست"].astype(str),
        "توضیحات_f":    df_all["توضیحات فاکتور"].astype(str),
        "کد انبار":      2,
        "کد کالا":       df_all["کد کالا"],
        "نام کالا":      df_all["نام کالا"],
        "کد قدیم":      "",
        "مقدار":        df_all["تعداد"],
        "قیمت":         df_all["قیمت"],
        "مبلغ کالا":    df_all["قیمت"] * df_all["تعداد"],
        "مبلغ تخفیف":   0.0,
        "مبلغ مالیات":  0.0,
        "اضافات":       0.0,
        "radif":        df_all.groupby("شماره فاکتور").cumcount() + 1
    })

    # 5) منطق تخفیف/اضافات/مالیات — عین نسخه GUI
    new_rows = []
    for fac in df_out["شماره فاکتور"].unique():
        sub_all = df_all[df_all["شماره فاکتور"] == fac]
        sub_out = df_out[df_out["شماره فاکتور"] == fac]

        # اولین مقدار هر فاکتور برای تخفیف/اضافات
        disc_amt = sub_all[sub_all["تخفیف"] > 0]["تخفیف"].iloc[:1].sum()
        add_amt  = sub_all[sub_all["اضافات"] > 0]["اضافات"].iloc[:1].sum()

        # --- اضافات ---
        first = sub_out.iloc[0]
        if 0 < add_amt <= 1_100_000:
            df_out.loc[df_out["شماره فاکتور"] == fac, "اضافات"] = 0
            freight_name = sub_all.loc[sub_all["کد کالا"] == 5, "نام کالا"].iloc[0] if (sub_all["کد کالا"] == 5).any() else ""
            new_rows.append({
                **first.to_dict(),
                "کد کالا": 10000, "نام کالا": freight_name,
                "مقدار": 0, "قیمت": 0, "مبلغ کالا": 0,
                "اضافات": add_amt, "radif": sub_out["radif"].max() + 1
            })
        elif add_amt > 1_100_000:
            df_out.loc[df_out["شماره فاکتور"] == fac, "اضافات"] = 0
            eq_mask = (df_out["شماره فاکتور"] == fac) & (df_out["مبلغ کالا"] == add_amt)
            df_out.loc[eq_mask, ["مقدار", "قیمت", "مبلغ کالا"]] = 0
            new_rows.append({
                **first.to_dict(),
                "کد کالا": 6121, "نام کالا": "اضافات",
                "مقدار": 1, "قیمت": add_amt, "مبلغ کالا": add_amt,
                "مبلغ مالیات": round(0.1 * add_amt), "اضافات": 0,
                "radif": sub_out["radif"].max() + 1
            })

        # --- تخفیف: اگر ورودی تخفیف داشته باشد → ۱۰٪ هر ردیف (به‌جز 10000/6121)
        has_discount_in_input = (sub_all["تخفیف"] > 0).any()
        if has_discount_in_input:
            for idx in sub_out.index:
                code = df_out.at[idx, "کد کالا"]
                if code in (10000, 6121):
                    df_out.at[idx, "مبلغ تخفیف"] = 0.0
                else:
                    df_out.at[idx, "مبلغ تخفیف"] = round(0.10 * df_out.at[idx, "مبلغ کالا"])
        else:
            df_out.loc[sub_out.index, "مبلغ تخفیف"] = 0.0

        # --- مالیات: ۱۰٪ مبلغِ پس از تخفیف برای هر ردیف ---
        for idx in sub_out.index:
            taxable = df_out.at[idx, "مبلغ کالا"] - df_out.at[idx, "مبلغ تخفیف"]
            df_out.at[idx, "مبلغ مالیات"] = round(0.10 * max(taxable, 0))

    if new_rows:
        df_out = pd.concat([df_out, pd.DataFrame(new_rows)], ignore_index=True)

    # معافیت مالیاتی برای کدهای مشخص‌شده
    df_out.loc[df_out["کد کالا"].isin(TAX_EXEMPT_CODES), "مبلغ مالیات"] = 0

    # 6) مرتب‌سازی و تخصیص شناسه/سریال
    first_dates = df_out.groupby("شماره فاکتور")["تاریخ"].min()
    sorted_facs = first_dates.sort_values().index
    df_out = pd.concat(
        [df_out[df_out["شماره فاکتور"] == f].sort_values("radif") for f in sorted_facs],
        ignore_index=True
    )

    uniq = df_out["شماره فاکتور"].drop_duplicates().tolist()
    id_map     = {f: start_id     + i for i, f in enumerate(uniq)}
    serial_map = {f: start_serial + i for i, f in enumerate(uniq)}
    df_out["شناسه"]       = df_out["شماره فاکتور"].map(id_map).astype(int)
    df_out["شماره سریال"] = df_out["شماره فاکتور"].map(serial_map).astype(int)

    # 7) اصلاح «اسنپ فود» و حذف ستون کمکی
    snap_mask = df_out["توضیحات_f"].str.contains("اسنپ فود", case=False, na=False)
    df_out.loc[snap_mask, ["کد مشتری", "نام مشتری"]] = [2251, "اسنپ فود"]
    df_out.drop(columns=["توضیحات_f"], inplace=True)

    # 8) ساخت جدول محاسبه
    for df in (df_sal, df_bi):
        if "توضیحات فاکتور" not in df.columns:
            cols = [c for c in df.columns if "توضیح" in c or "توضیحات" in c]
            df["توضیحات فاکتور"] = df[cols[0]].astype(str) if cols else ""

    df_input = pd.concat([df_sal, df_bi], ignore_index=True)

    cnt_sal   = len(df_sal)
    cnt_bi    = len(df_bi)
    cnt_in    = cnt_sal + cnt_bi
    cnt_out   = len(df_out)
    cnt_extra = df_out["کد کالا"].isin([10000, 6121]).sum()

    disc_in_per  = df_input[df_input["تخفیف"] > 0].groupby("شماره فاکتور")["تخفیف"].first()
    disc_out_per = df_out.groupby("شماره فاکتور")["مبلغ تخفیف"].sum()
    disc_diff_ids = [
        fid for fid in sorted(set(disc_in_per.index).union(disc_out_per.index))
        if disc_in_per.get(fid, 0) != disc_out_per.get(fid, 0)
    ]
    disc_in  = disc_in_per.sum()
    disc_out = disc_out_per.sum()

    sales_in_per = (df_input["قیمت"].mul(df_input["تعداد"])
                    .groupby(df_input["شماره فاکتور"]).sum())
    sales_out_per = (df_out[~df_out["کد کالا"].isin([10000, 6121])]
                     .groupby("شماره فاکتور")["مبلغ کالا"].sum())
    sales_diff_ids = [
        fid for fid in sorted(set(sales_in_per.index).union(sales_out_per.index))
        if sales_in_per.get(fid, 0) != sales_out_per.get(fid, 0)
    ]
    sales_in  = sales_in_per.sum()
    sales_out = sales_out_per.sum()

    add_in_per  = df_input[df_input["اضافات"] > 0].groupby("شماره فاکتور")["اضافات"].first()
    add_out_per = (df_out["اضافات"].add(df_out["مبلغ کالا"].where(df_out["کد کالا"] == 6121, 0))
                   .groupby(df_out["شماره فاکتور"]).sum())
    add_diff_ids = [
        fid for fid in sorted(set(add_in_per.index).union(add_out_per.index))
        if add_in_per.get(fid, 0) != add_out_per.get(fid, 0)
    ]
    add_in  = add_in_per.sum()
    add_out = add_out_per.sum()

    tax_in_per  = df_input.groupby("شماره فاکتور")["مالیات"].first()
    tax_out_per = df_out.groupby("شماره فاکتور")["مبلغ مالیات"].sum()
    tax_diff_ids = [
        fid for fid in sorted(set(tax_in_per.index).union(tax_out_per.index))
        if tax_in_per.get(fid, 0) != tax_out_per.get(fid, 0)
    ]
    tax_in  = tax_in_per.sum()
    tax_out = tax_out_per.sum()

    rows = [
        {"شرح":"جمع تعداد رکوردهای ورودی",        "مقدار": cnt_in,       "شماره‌فاکتور اختلاف": ""},
        {"شرح":"جمع تعداد رکوردهای خروجی",         "مقدار": cnt_out,      "شماره‌فاکتور اختلاف": ""},
        {"شرح":"اختلاف ورودی و خروجی",            "مقدار": cnt_in - cnt_out, "شماره‌فاکتور اختلاف": ""},
        {"شرح":"تعداد ردیف‌های کالای 10000 و 6121", "مقدار": cnt_extra,    "شماره‌فاکتور اختلاف": ""},
        {"شرح":"جمع تخفیف ورودی",                  "مقدار": disc_in,      "شماره‌فاکتور اختلاف": ""},
        {"شرح":"جمع تخفیف خروجی",                  "مقدار": disc_out,     "شماره‌فاکتور اختلاف": ",".join(map(str, disc_diff_ids))},
        {"شرح":"جمع فروش ورودی",                   "مقدار": sales_in,     "شماره‌فاکتور اختلاف": ""},
        {"شرح":"جمع فروش خروجی (بدون 10000/6121)", "مقدار": sales_out,    "شماره‌فاکتور اختلاف": ",".join(map(str, sales_diff_ids))},
        {"شرح":"جمع اضافات ورودی",                 "مقدار": add_in,       "شماره‌فاکتور اختلاف": ""},
        {"شرح":"جمع اضافات خروجی",                 "مقدار": add_out,      "شماره‌فاکتور اختلاف": ",".join(map(str, add_diff_ids))},
        {"شرح":"جمع مالیات ورودی (هر فاکتور یک بار)","مقدار": tax_in,    "شماره‌فاکتور اختلاف": ""},
        {"شرح":"جمع مالیات خروجی",                 "مقدار": tax_out,      "شماره‌فاکتور اختلاف": ",".join(map(str, tax_diff_ids))},
        {"شرح":"اسنپ فود و کد مشتری دستی چک شود",  "مقدار": "",           "شماره‌فاکتور اختلاف": ""}
    ]
    df_calc = pd.DataFrame(rows)

    # 9) ذخیره خروجی
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_out.to_excel(writer, sheet_name="خروجی", index=False)
        df_calc.to_excel(writer, sheet_name="محاسبه", index=False)

    # 10) به‌روزرسانی state برای دفعات بعد
    save_last_used(df_out)