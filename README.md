# VN30 — Bảng chọn mã hàng tháng

Công cụ cá nhân: mỗi cuối tháng mở lên, xem hệ thống gợi ý 3 mã VN30 nên vào lệnh
tháng tới, dựa trên chiến lược **Mùa vụ (walk-forward, chuỗi 4 năm) + Momentum (3 tháng)**
đã kiểm chứng.

⚠️ **Đây là công cụ tham khảo, không phải lời khuyên đầu tư.** Mọi con số đều từ
backtest lịch sử — không đảm bảo lặp lại trong tương lai. Tự chịu trách nhiệm với
quyết định giao dịch của mình.

## Cấu trúc project

```
vn30-strategy/
├── fetch_data.py          # Lấy dữ liệu VN30 (chạy chậm, rate-limited)
├── analysis.py             # Chạy walk-forward, xuất recommendations.json
├── requirements.txt
├── data/
│   └── vn30_all_daily.csv  # Dữ liệu (tự tạo sau khi chạy fetch_data.py)
├── frontend/                # React app (Vite)
│   ├── src/App.jsx
│   └── public/recommendations.json  # (tự tạo sau khi chạy analysis.py)
└── .github/workflows/
    └── daily_fetch.yml     # Tự động chạy mỗi sáng qua GitHub Actions (tùy chọn)
```

## Cài đặt lần đầu

### 1. Phần dữ liệu (Python)

```bash
pip install -r requirements.txt
python fetch_data.py       # Lần đầu sẽ tải từ 2015 — mất khá lâu (rate-limited)
python analysis.py         # Xuất ra frontend/public/recommendations.json
```

### 2. Phần giao diện (React)

```bash
cd frontend
npm install
npm run dev                # Mở http://localhost:5173
```

## Sử dụng hàng tháng

Đầu mỗi tháng, chạy lại 2 lệnh này (dữ liệu mới + tính lại gợi ý):

```bash
python fetch_data.py
python analysis.py
```

Sau đó mở `frontend` (`npm run dev`, hoặc dùng bản đã build — xem dưới) để xem
Top 3 mã của tháng.

### Build bản tĩnh để mở nhanh (không cần chạy `npm run dev` mỗi lần)

```bash
cd frontend
npm run build
```

File tĩnh nằm trong `frontend/dist/` — mở `dist/index.html` trực tiếp bằng trình
duyệt bất cứ lúc nào (không cần chạy server), miễn là `recommendations.json` đã
được copy vào `dist/` cùng thư mục (build tự làm việc này vì file nằm trong `public/`).

## Chạy nền tự động mỗi sáng

### Cách 1 — GitHub Actions (khuyến nghị, không cần máy tính bật)

1. Đẩy project này lên 1 GitHub repo (`git init && git add . && git commit -m "init" && git push`).
2. Workflow `.github/workflows/daily_fetch.yml` đã cấu hình sẵn chạy **8h sáng mỗi ngày**
   (giờ Việt Nam), tự lấy dữ liệu mới + tính lại gợi ý + commit ngược vào repo.
3. Có thể bấm chạy tay bất kỳ lúc nào ở tab **Actions** trên GitHub (nút "Run workflow").
4. Deploy `frontend/` lên GitHub Pages / Vercel / Netlify (miễn phí) để có 1 link cố định
   mở lên bất cứ đâu — không cần cài gì trên máy.

### Cách 2 — Cron job trên máy cá nhân (Linux/Mac)

```bash
crontab -e
```

Thêm dòng (chạy 8h sáng mỗi ngày):

```
0 8 * * * cd /đường/dẫn/tới/vn30-strategy && /usr/bin/python3 fetch_data.py >> logs/fetch.log 2>&1
```

### Cách 3 — Task Scheduler trên Windows

Tạo Basic Task → Trigger: Daily 8:00 AM → Action: chạy `python.exe fetch_data.py`,
"Start in" trỏ vào thư mục `vn30-strategy`.

## Điều chỉnh tham số chiến lược

Mở `analysis.py`, sửa các hằng số đầu file:

```python
MIN_CHAIN = 4                # so nam lich su toi thieu de xet mua vu
MOM_DAYS = 90                 # do dai momentum (ngay)
W_SEASONAL = 0.2              # trong so mua vu
W_MOMENTUM = 0.8              # trong so momentum
TRANSACTION_COST_PCT = 0.40   # % chi phi (phi moi gioi 2 chieu + thue) MOI lan mua-ban
```

Các giá trị mặc định (`W_SEASONAL=0.2, W_MOMENTUM=0.8`) là kết quả grid-search
tối ưu cho VN30 — xem lại lịch sử phân tích nếu muốn thử tham số khác.

`TRANSACTION_COST_PCT=0.40` là mức trung bình (phí môi giới ~0.15%/chiều × 2 +
thuế TNCN cố định 0.1% trên giá trị bán). **Nên chỉnh lại đúng biểu phí công ty
chứng khoán bạn đang dùng** để số liệu hiển thị (CAGR, Max DD...) sát thực tế nhất —
tất cả thống kê trong app đều đã trừ chi phí này, không phải con số lý tưởng hóa.

## Lưu ý quan trọng

- `fetch_data.py` cố tình chạy **chậm** (nghỉ 2 giây giữa mỗi mã) để tránh bị chặn API —
  đừng giảm `DELAY_SECONDS` xuống quá thấp.
- Dữ liệu cần **ít nhất 4 năm lịch sử liên tục** cho mỗi mã mới có đủ điều kiện xét chọn
  (yêu cầu `MIN_CHAIN`) — mã mới niêm yết sẽ không xuất hiện trong gợi ý cho đến khi đủ dữ liệu.
- Kết quả backtest (~29-53%/năm tùy trọng số) đã được kiểm chứng qua walk-forward và
  bootstrap, nhưng **vẫn chỉ dựa trên 6-10 năm dữ liệu lịch sử** — không phải cam kết
  cho tương lai.
