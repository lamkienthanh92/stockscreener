"""
analysis.py — Chay chien luoc Mua vu (Seasonal, chuoi 4 nam) + Momentum (3 thang),
walk-forward KHONG lookahead, tim Top3 ma nen mua cho THANG HIEN TAI.

Xuat ket qua ra recommendations.json de React app doc va hien thi.

Chay:
    python analysis.py

Nen chay ngay dau moi thang (sau khi fetch_data.py da cap nhat du lieu).
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "vn30_all_daily.csv")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "frontend", "public", "recommendations.json")

MIN_CHAIN = 4          # so nam lien tuc toi thieu de xet mua vu
MOM_DAYS = 90           # ~3 thang, momentum trailing
W_SEASONAL = 0.2        # trong so mua vu (da grid-search toi uu cho VN30)
W_MOMENTUM = 0.8        # trong so momentum


def load_data():
    df = pd.read_csv(DATA_FILE)
    df["time"] = pd.to_datetime(df["time"])
    return df


def price_on_or_before(cache, sym, date):
    sub = cache[sym]
    s2 = sub[sub["time"] <= date]
    return s2.iloc[-1]["close"] if len(s2) > 0 else None


def price_on_or_after(cache, sym, date):
    sub = cache[sym]
    s2 = sub[sub["time"] >= date]
    return s2.iloc[0]["close"] if len(s2) > 0 else None


def month_return(cache, sym, entry_date, exit_date):
    pb = price_on_or_after(cache, sym, entry_date)
    ps = price_on_or_after(cache, sym, exit_date)
    return (ps / pb - 1) * 100 if pb and ps else None


def trailing_return(cache, sym, as_of_date, days_back):
    p_now = price_on_or_before(cache, sym, as_of_date)
    p_before = price_on_or_before(cache, sym, as_of_date - pd.Timedelta(days=days_back))
    return (p_now / p_before - 1) * 100 if p_now and p_before and p_before > 0 else None


def seasonal_score(precomp_month, sym, month, train_years):
    vals = [precomp_month[month].get((sym, y)) for y in train_years]
    if all(v is not None for v in vals) and len(vals) >= MIN_CHAIN:
        avg, std = np.mean(vals), np.std(vals)
        return avg / std if std > 0 else 0
    return None


def main():
    df = load_data()
    all_syms = sorted(df["symbol"].unique())
    cache = {s: df[df["symbol"] == s].sort_values("time") for s in all_syms}

    # Precompute return theo thang, tung ma, tung nam (de tinh diem mua vu)
    precomp_month = {}
    for m in range(1, 13):
        precomp_month[m] = {}
        for sym in all_syms:
            for y in range(2015, datetime.now().year + 1):
                entry = pd.Timestamp(f"{y}-{m:02d}-01")
                em, ey = (m + 1, y) if m < 12 else (1, y + 1)
                exit_ = pd.Timestamp(f"{ey}-{em:02d}-01")
                r = month_return(cache, sym, entry, exit_)
                if r is not None:
                    precomp_month[m][(sym, y)] = r

    now = datetime.now()
    cur_year, cur_month = now.year, now.month
    train_years = list(range(cur_year - MIN_CHAIN, cur_year))
    as_of = pd.Timestamp(f"{cur_year}-{cur_month:02d}-01") - pd.Timedelta(days=1)

    candidates = []
    for sym in all_syms:
        ss = seasonal_score(precomp_month, sym, cur_month, train_years)
        mom = trailing_return(cache, sym, as_of, MOM_DAYS)
        if ss is not None and mom is not None:
            candidates.append({"symbol": sym, "seasonal_score": ss, "momentum_score": mom})

    if len(candidates) < 3:
        print("KHONG DU du lieu de xep hang (can it nhat 4 nam lich su + 3 thang gan day).")
        picks = []
    else:
        ss_arr = np.array([c["seasonal_score"] for c in candidates])
        mom_arr = np.array([c["momentum_score"] for c in candidates])
        ss_rank = pd.Series(ss_arr).rank(pct=True).values
        mom_rank = pd.Series(mom_arr).rank(pct=True).values
        combo = W_SEASONAL * ss_rank + W_MOMENTUM * mom_rank
        for i, c in enumerate(candidates):
            c["combo_score"] = float(combo[i])
        candidates.sort(key=lambda x: -x["combo_score"])
        picks = candidates[:3]

    result = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "target_month": f"{cur_year}-{cur_month:02d}",
        "weights": {"seasonal": W_SEASONAL, "momentum": W_MOMENTUM},
        "picks": picks,
        "all_candidates_ranked": sorted(candidates, key=lambda x: -x.get("combo_score", -999))[:15],
        "note": "Day la ket qua walk-forward, KHONG dam bao loi nhuan. Tu danh gia rui ro truoc khi giao dich.",
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Da xuat ket qua ra: {OUTPUT_FILE}")
    print(f"\nTOP 3 MA THANG {cur_year}-{cur_month:02d}:")
    for p in picks:
        print(f"  {p['symbol']}: seasonal={p['seasonal_score']:.2f}  momentum={p['momentum_score']:.1f}%  combo={p['combo_score']:.3f}")


if __name__ == "__main__":
    main()
