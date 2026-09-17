"""
fetch_data.py — Lấy dữ liệu daily VN30 từ vnstock, chạy CHẬM (rate-limited)
để tránh bị chặn API. Thiết kế để chạy MỖI SÁNG qua cron job — chỉ cập nhật
phần dữ liệu MỚI (incremental), không tải lại từ đầu mỗi lần.

Cài đặt:
    pip install -r requirements.txt

Chạy tay:
    python fetch_data.py

Chạy tự động mỗi sáng (Linux/Mac, qua cron) — xem hướng dẫn cuối file.
"""

import pandas as pd
import time
import os
from datetime import datetime, timedelta
from vnstock import Vnstock, Listing

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "vn30_all_daily.csv")
DELAY_SECONDS = 2.0          # nghỉ giữa mỗi mã — CHẬM để tránh bị chặn API
START_DATE_IF_NEW = "2015-01-01"


def get_vn30_symbols():
    listing = Listing(source="KBS")
    return listing.symbols_by_group(group="VN30").tolist()


def load_existing():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df["time"] = pd.to_datetime(df["time"])
        return df
    return None


def fetch_one_symbol(sym, start, end):
    try:
        stock = Vnstock().stock(symbol=sym, source="KBS")
        df = stock.quote.history(start=start, end=end, interval="1D")
        if df is None or df.empty:
            return None
        df["symbol"] = sym
        return df[["symbol", "time", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        print(f"  Loi voi {sym}: {e}")
        return None


def main():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    symbols = get_vn30_symbols()
    print(f"So ma VN30: {len(symbols)}")

    existing = load_existing()
    today = datetime.now().strftime("%Y-%m-%d")

    new_rows = []
    for i, sym in enumerate(symbols):
        # Neu da co du lieu cho ma nay, chi tai phan MOI (tu ngay cuoi cung + 1)
        if existing is not None and sym in existing["symbol"].unique():
            last_date = existing[existing["symbol"] == sym]["time"].max()
            start = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
            if start >= today:
                print(f"[{i+1}/{len(symbols)}] {sym}: da cap nhat, bo qua")
                continue
        else:
            start = START_DATE_IF_NEW

        print(f"[{i+1}/{len(symbols)}] Dang tai {sym} tu {start}...")
        df = fetch_one_symbol(sym, start, today)
        if df is not None and not df.empty:
            new_rows.append(df)
            print(f"  -> +{len(df)} dong moi")
        time.sleep(DELAY_SECONDS)   # CHAM lai, tranh bi chan API

    if new_rows:
        new_df = pd.concat(new_rows, ignore_index=True)
        if existing is not None:
            combined = pd.concat([existing, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["symbol", "time"], keep="last")
        else:
            combined = new_df
        combined = combined.sort_values(["symbol", "time"])
        combined.to_csv(DATA_FILE, index=False)
        print(f"\nDA CAP NHAT: {len(new_df)} dong moi. Tong: {len(combined)} dong -> {DATA_FILE}")
    else:
        print("\nKhong co du lieu moi nao (co the da chay roi hom nay).")


if __name__ == "__main__":
    main()

# ============================================================
# HUONG DAN CHAY TU DONG MOI SANG (cron, Linux/Mac):
#
#   1. Mo terminal, go: crontab -e
#   2. Them dong nay (chay 8h sang moi ngay):
#      0 8 * * * cd /duong/dan/toi/vn30-strategy && /usr/bin/python3 fetch_data.py >> logs/fetch.log 2>&1
#
# Windows (Task Scheduler):
#   Tao Basic Task -> Trigger: Daily 8:00 AM
#   Action: Start a program -> python.exe -> Arguments: fetch_data.py
#   Start in: duong dan toi thu muc vn30-strategy
# ============================================================
