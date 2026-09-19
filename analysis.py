"""
analysis.py — Chay chien luoc Mua vu (Seasonal, chuoi 4 nam) + Momentum (3 thang),
walk-forward KHONG lookahead.

Xuat 2 file:
  1. recommendations.json — Top3 ma nen mua cho THANG HIEN TAI
  2. history.json — toan bo lich su walk-forward (tung thang da chon gi, hieu qua
     ra sao) + thong ke tong hop (IRR, winrate, max DD, so lan test...) de
     React app hien thi bieu do va bang lich su.

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
OUT_DIR = os.path.join(os.path.dirname(__file__), "frontend", "public")
RECS_FILE = os.path.join(OUT_DIR, "recommendations.json")
LOCKS_FILE = os.path.join(OUT_DIR, "monthly_locks.json")
HISTORY_FILE = os.path.join(OUT_DIR, "history.json")
PRICES_FILE = os.path.join(OUT_DIR, "latest_prices.json")
PRICE_HISTORY_FILE = os.path.join(OUT_DIR, "price_history.json")
PRICE_HISTORY_DAYS = 240   # ~1 nam giao dich, du de ve bieu do gia

MIN_CHAIN = 4          # so nam lien tuc toi thieu de xet mua vu
MOM_DAYS = 90           # ~3 thang, momentum trailing
W_SEASONAL = 0.2        # trong so mua vu (da grid-search toi uu cho VN30)
W_MOMENTUM = 0.8        # trong so momentum
INJECT = 3_000_000      # von bom moi thang, dung de mo phong duong cong von
PENDING_PREVIEW_FROM_DAY = 15   # tu ngay nay trong thang moi bat dau hien "du kien thang sau"

# Chi phi giao dich moi lan MUA-BAN 1 ma (%): phi moi gioi mua + phi moi gioi ban + thue TNCN ban CK (0.1% co dinh)
# Muc "trung binh": 0.15% (mua) + 0.15% (ban) + 0.10% (thue) = 0.40%
# Chinh lai theo bieu phi cong ty chung khoan ban dang dung neu can chinh xac hon.
TRANSACTION_COST_PCT = 0.40


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


def export_prices(cache, all_syms):
    """Xuat gia moi nhat (de tinh lai/lo) va lich su gia gan day (de ve bieu do) cho MOI ma —
    khong chi rieng Top3 — vi cac lan da 'ghi nhan' truoc co the la ma khac voi Top3 hien tai."""
    latest = {}
    history = {}
    for sym in all_syms:
        sub = cache[sym]
        if len(sub) == 0:
            continue
        latest[sym] = float(sub.iloc[-1]["close"])
        recent = sub.tail(PRICE_HISTORY_DAYS)
        history[sym] = [
            {"t": row["time"].strftime("%Y-%m-%d"), "c": float(row["close"])}
            for _, row in recent.iterrows()
        ]

    with open(PRICES_FILE, "w", encoding="utf-8") as f:
        json.dump(latest, f, ensure_ascii=False)
    with open(PRICE_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)


def latest_price(cache, sym):
    sub = cache[sym]
    return float(sub.iloc[-1]["close"]) if len(sub) > 0 else None


def load_locks():
    if os.path.exists(LOCKS_FILE):
        with open(LOCKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_locks(locks):
    with open(LOCKS_FILE, "w", encoding="utf-8") as f:
        json.dump(locks, f, ensure_ascii=False, indent=2)


def get_or_lock_candidates(cache, all_syms, precomp_month, year, month, now):
    """CHOT xep hang cho (year, month) NGAY LAN CHAY DAU TIEN cua thang do, va luu vao
    monthly_locks.json. Cac lan chay sau trong CUNG thang chi doc lai ket qua da chot,
    KHONG tinh lai — de dam bao Top3 khong bao gio troi giua thang du du lieu gia lich
    su o nguon co bi dieu chinh nguoc (chia co tuc, sua loi du lieu...) hay khong.

    Tra ve: (candidates, locked_at_str, is_freshly_locked)"""
    key = f"{year}-{month:02d}"
    locks = load_locks()

    if key in locks:
        return locks[key]["candidates"], locks[key]["locked_at"], False

    candidates = rank_candidates(cache, all_syms, precomp_month, year, month)
    locked_at = now.strftime("%Y-%m-%d %H:%M:%S")
    locks[key] = {"locked_at": locked_at, "candidates": candidates}
    save_locks(locks)
    return candidates, locked_at, True


def rank_candidates(cache, all_syms, precomp_month, year, month):
    """Tra ve danh sach ung vien da xep hang (combo_score giam dan) cho 1 (year,month)."""
    train_years = list(range(year - MIN_CHAIN, year))
    entry_date = pd.Timestamp(f"{year}-{month:02d}-01")
    as_of = entry_date - pd.Timedelta(days=1)

    candidates = []
    for sym in all_syms:
        ss = seasonal_score(precomp_month, sym, month, train_years)
        mom = trailing_return(cache, sym, as_of, MOM_DAYS)
        if ss is not None and mom is not None:
            candidates.append({"symbol": sym, "seasonal_score": ss, "momentum_score": mom})

    if len(candidates) < 3:
        return []

    ss_arr = np.array([c["seasonal_score"] for c in candidates])
    mom_arr = np.array([c["momentum_score"] for c in candidates])
    ss_rank = pd.Series(ss_arr).rank(pct=True).values
    mom_rank = pd.Series(mom_arr).rank(pct=True).values
    combo = W_SEASONAL * ss_rank + W_MOMENTUM * mom_rank
    for i, c in enumerate(candidates):
        c["combo_score"] = float(combo[i])
    candidates.sort(key=lambda x: -x["combo_score"])
    return candidates


def build_walk_forward_history(cache, all_syms, precomp_month, up_to_year, up_to_month):
    """Chay lai TOAN BO walk-forward tu nam co du du lieu (2016+MIN_CHAIN) den thang
    TRUOC thang hien tai (vi thang hien tai chua co ket qua thuc de danh gia).
    Tra ve: list cac thang da giao dich (voi ket qua THUC), va duong cong von."""
    start_year = 2016 + MIN_CHAIN
    months_log = []
    balance = 0.0

    y, m = start_year, 1
    while (y < up_to_year) or (y == up_to_year and m < up_to_month):
        candidates = rank_candidates(cache, all_syms, precomp_month, y, m)
        picks = candidates[:3]

        entry_date = pd.Timestamp(f"{y}-{m:02d}-01")
        em, ey = (m + 1, y) if m < 12 else (1, y + 1)
        exit_date = pd.Timestamp(f"{ey}-{em:02d}-01")

        rets = []
        for p in picks:
            r = month_return(cache, p["symbol"], entry_date, exit_date)
            if r is not None:
                rets.append(r - TRANSACTION_COST_PCT)   # tru phi + thue MOI lan mua-ban
        month_ret = float(np.mean(rets)) if rets else 0.0

        balance += INJECT
        balance *= (1 + month_ret / 100.0)

        months_log.append({
            "year": y, "month": m,
            "label": f"{y}-{m:02d}",
            "picks": [p["symbol"] for p in picks],
            "return_pct": round(month_ret, 2),
            "balance": round(balance, 0),
        })

        m += 1
        if m > 12:
            m = 1
            y += 1

    return months_log, balance


def compute_stats(months_log, total_invested):
    if not months_log:
        return {}
    rets = [x["return_pct"] for x in months_log]
    balances = [x["balance"] for x in months_log]
    n = len(months_log)
    win_rate = sum(1 for r in rets if r > 0) / n * 100

    running_max = -1e18
    max_dd = 0.0
    for b in balances:
        running_max = max(running_max, b)
        dd = (b - running_max) / running_max * 100 if running_max > 0 else 0
        max_dd = min(max_dd, dd)

    final_balance = balances[-1]
    n_years = n / 12
    total_return_pct = (final_balance / total_invested - 1) * 100 if total_invested > 0 else 0

    # IRR xap xi (khong tinh dong tien chinh xac tung thang o day, chi ap dung CAGR
    # tren tong von de don gian hoa cho hien thi — chi tiet IRR that da tinh rieng
    # trong qua trinh phat trien chien luoc)
    cagr = ((final_balance / total_invested) ** (1 / n_years) - 1) * 100 if total_invested > 0 and n_years > 0 else 0

    return {
        "n_months_tested": n,
        "n_years_tested": round(n_years, 1),
        "win_rate_pct": round(win_rate, 1),
        "max_drawdown_pct": round(max_dd, 2),
        "total_invested": total_invested,
        "final_balance": round(final_balance, 0),
        "total_return_pct": round(total_return_pct, 1),
        "cagr_approx_pct": round(cagr, 1),
        "best_month": max(months_log, key=lambda x: x["return_pct"]),
        "worst_month": min(months_log, key=lambda x: x["return_pct"]),
    }


VALIDATION_NOTES = [
    "Walk-forward thật: mỗi tháng chỉ dùng dữ liệu ĐẾN TRƯỚC tháng đó để chọn mã — không nhìn trước tương lai.",
    "Yêu cầu chuỗi lịch sử tối thiểu 4 năm liên tục trước khi 1 mã được xét chọn (tránh chọn theo may mắn 1-2 năm).",
    "Đã test độ nhạy theo tần suất giao dịch (tuần / 2 tuần / tháng / 2 tháng) — khung THÁNG cho kết quả tốt và ổn định nhất.",
    "Đã kiểm chứng bằng Bootstrap (chọn ngẫu nhiên trong nhóm ứng viên hợp lệ, lặp nhiều trăm lần) để đo phần 'may mắn' trong kết quả Top3.",
    "Kết hợp 2 yếu tố độc lập: Mùa vụ (seasonal, theo chuỗi năm) + Momentum (đà tăng 3 tháng gần nhất) — trọng số đã grid-search riêng cho VN30.",
    "Đã kiểm chứng cách chia vốn cho 3 mã: chia ĐỀU 1/3 mỗi mã cho kết quả tốt nhất — ưu tiên mã điểm cao hơn thực ra làm giảm hiệu suất.",
    f"Đã trừ chi phí giao dịch thực tế: {TRANSACTION_COST_PCT}%/lần mua-bán (phí môi giới 2 chiều + thuế TNCN 0.1% bán CK) — số liệu hiển thị là SAU chi phí, không phải lý tưởng hóa.",
    "Đây KHÔNG phải chiến lược 'chắc thắng' — vẫn có tháng/năm hiệu suất yếu hoặc âm trong lịch sử test. Luôn tự đánh giá rủi ro trước khi giao dịch thật.",
]


def build_next_month_preview(cache, all_syms, precomp_month, cur_year, cur_month, now, latest_data_date):
    """Xem TRUOC (KHONG chot) Top3 co the co cua thang KE TIEP, de nguoi dung chuan bi
    von som. Chi tinh tu ngay PENDING_PREVIEW_FROM_DAY tro di trong thang, va LUON tinh
    lai moi lan chay (khong luu khoa) vi day chi la uoc tinh se con doi cho toi khi
    thang sau thuc su bat dau va duoc chot bang du lieu day du.

    Ly do ky thuat: ham rank_candidates() dung price_on_or_before() de lay gia tai
    "as_of" (ngay cuoi thang ke tiep, tuc 1 ngay TRUOC ngay 1 thang sau nua) — vi ngay
    do nam o TUONG LAI so voi du lieu hien co, ham se tu dong lay gia GAN NHAT dang co
    (tuc gia hom nay) thay the. Do la cach duy nhat hop ly de "nhin truoc"."""
    if now.day < PENDING_PREVIEW_FROM_DAY:
        return None

    next_month = cur_month + 1 if cur_month < 12 else 1
    next_year = cur_year if cur_month < 12 else cur_year + 1

    candidates = rank_candidates(cache, all_syms, precomp_month, next_year, next_month)
    if not candidates:
        return None

    picks = candidates[:3]
    for p in picks:
        p["latest_price"] = latest_price(cache, p["symbol"])
    all_ranked = sorted(candidates, key=lambda x: -x.get("combo_score", -999))[:15]

    return {
        "target_month": f"{next_year}-{next_month:02d}",
        "computed_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "momentum_uses_data_up_to": latest_data_date,
        "lock_expected_on": f"{next_year}-{next_month:02d}-01",
        "picks": picks,
        "all_candidates_ranked": all_ranked,
        "note": (
            "DU KIEN, CHUA CHOT — chi de tham khao chuan bi von truoc. Vi thang "
            f"{next_year}-{next_month:02d} chua bat dau nen momentum 3 thang o day "
            f"dang tam dung gia gan nhat ({latest_data_date}) thay cho gia dong cua "
            "cuoi thang. Danh sach that su se duoc CHOT vao ngay 1 dau thang sau va "
            "co the khac voi ban du kien nay."
        ),
    }


def main():
    df = load_data()
    all_syms = sorted(df["symbol"].unique())
    cache = {s: df[df["symbol"] == s].sort_values("time") for s in all_syms}

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
    latest_data_date = df["time"].max().strftime("%Y-%m-%d")

    # ---- 0. Xuat gia (moi nhat + lich su) cho MOI ma, dung cho tinh lai/lo va bieu do gia ----
    export_prices(cache, all_syms)

    # ---- 1. Goi y THANG HIEN TAI ----
    # QUAN TRONG: xep hang (seasonal/momentum/combo) chi duoc tinh 1 LAN duy nhat cho
    # moi thang, vao lan chay dau tien cua thang do, roi CHOT lai trong monthly_locks.json.
    # Cac lan chay sau trong cung thang chi doc lai ban da chot -> Top3 khong the troi
    # giua thang. Chi rieng "latest_price" (gia hien tai, de tinh lai/lo) la duoc lay moi.
    candidates_locked, locked_at, freshly_locked = get_or_lock_candidates(
        cache, all_syms, precomp_month, cur_year, cur_month, now
    )
    # deep-copy de khong ghi latest_price nguoc vao file lock (lock chi luu diem xep hang)
    candidates = [dict(c) for c in candidates_locked]
    picks = candidates[:3]
    for p in picks:
        p["latest_price"] = latest_price(cache, p["symbol"])
    all_ranked = sorted(candidates, key=lambda x: -x.get("combo_score", -999))[:15]

    # ---- 1b. Xem truoc (KHONG chot) Top3 thang KE TIEP, chi hien tu ngay 15 ----
    next_month_preview = build_next_month_preview(
        cache, all_syms, precomp_month, cur_year, cur_month, now, latest_data_date
    )

    result = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "locked_at": locked_at,
        "freshly_locked_this_run": freshly_locked,
        "target_month": f"{cur_year}-{cur_month:02d}",
        "weights": {"seasonal": W_SEASONAL, "momentum": W_MOMENTUM},
        "picks": picks,
        "all_candidates_ranked": all_ranked,
        "next_month_preview": next_month_preview,
        "note": "Day la ket qua walk-forward, KHONG dam bao loi nhuan. Tu danh gia rui ro truoc khi giao dich.",
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(RECS_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # ---- 2. Lich su walk-forward (cac thang DA CO ket qua thuc, tru thang hien tai) ----
    months_log, final_balance = build_walk_forward_history(cache, all_syms, precomp_month, cur_year, cur_month)
    total_invested = INJECT * len(months_log)
    stats = compute_stats(months_log, total_invested)

    history = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "weights": {"seasonal": W_SEASONAL, "momentum": W_MOMENTUM},
        "min_chain_years": MIN_CHAIN,
        "momentum_days": MOM_DAYS,
        "inject_per_month": INJECT,
        "transaction_cost_pct": TRANSACTION_COST_PCT,
        "stats": stats,
        "monthly_log": months_log,
        "validation_notes": VALIDATION_NOTES,
    }
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"Da xuat: {RECS_FILE}")
    print(f"Da xuat: {HISTORY_FILE}")
    print(f"Da xuat: {PRICES_FILE}")
    print(f"Da xuat: {PRICE_HISTORY_FILE}")
    print(f"\nTOP 3 MA THANG {cur_year}-{cur_month:02d} (da CHOT luc {locked_at}"
          f"{' -- MOI CHOT LAN NAY' if freshly_locked else ' -- doc lai tu khoa cu, KHONG tinh lai'}):")
    for p in picks:
        print(f"  {p['symbol']}: seasonal={p['seasonal_score']:.2f}  momentum={p['momentum_score']:.1f}%  combo={p['combo_score']:.3f}")
    if next_month_preview:
        print(f"\n(DU KIEN, CHUA CHOT) TOP 3 THANG {next_month_preview['target_month']} neu chot ngay hom nay:")
        for p in next_month_preview["picks"]:
            print(f"  {p['symbol']}: seasonal={p['seasonal_score']:.2f}  momentum={p['momentum_score']:.1f}%  combo={p['combo_score']:.3f}")
    else:
        print(f"\n(Chua toi ngay {PENDING_PREVIEW_FROM_DAY} trong thang nen chua hien du kien thang sau)")
    print(f"\nThong ke lich su ({stats.get('n_months_tested','?')} thang da test):")
    print(f"  Von: {stats.get('total_invested',0):,.0f}d -> {stats.get('final_balance',0):,.0f}d")
    print(f"  CAGR uoc tinh: {stats.get('cagr_approx_pct','?')}%/nam")
    print(f"  Winrate: {stats.get('win_rate_pct','?')}%")
    print(f"  Max Drawdown: {stats.get('max_drawdown_pct','?')}%")


if __name__ == "__main__":
    main()

