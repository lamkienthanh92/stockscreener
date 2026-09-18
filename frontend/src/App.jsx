import { useEffect, useState } from 'react'
import EquityChart from './EquityChart.jsx'
import PositionSizer from './PositionSizer.jsx'
import MonthlyReturnsBar from './MonthlyReturnsBar.jsx'
import { PriceInfoButton } from './PriceChart.jsx'

function fmtPct(v) {
  if (v === null || v === undefined) return '—'
  const sign = v >= 0 ? '+' : ''
  return `${sign}${v.toFixed(1)}%`
}

function fmtVND(v) {
  if (v === null || v === undefined) return '—'
  return v.toLocaleString('vi-VN') + 'đ'
}

function PctTag({ value }) {
  // Quy uoc VN: TANG (duong) = DO, GIAM (am) = XANH
  const up = value >= 0
  return (
    <span className={`pct-tag ${up ? 'pct-up' : 'pct-down'}`}>
      {fmtPct(value)}
    </span>
  )
}

export default function App() {
  const [data, setData] = useState(null)
  const [history, setHistory] = useState(null)
  const [error, setError] = useState(null)
  const [showAllHistory, setShowAllHistory] = useState(false)

  useEffect(() => {
    fetch('/recommendations.json')
      .then((r) => {
        if (!r.ok) throw new Error('Chưa có file recommendations.json — hãy chạy analysis.py trước.')
        return r.json()
      })
      .then(setData)
      .catch((e) => setError(e.message))

    fetch('/history.json')
      .then((r) => (r.ok ? r.json() : null))
      .then(setHistory)
      .catch(() => {})
  }, [])

  return (
    <div className="page">
      <header className="masthead">
        <div className="masthead-inner">
          <h1>VN30 · Bảng chọn mã</h1>
          <p className="subtitle">Walk-forward — Mùa vụ (chuỗi 4 năm) + Momentum (3 tháng)</p>
        </div>
      </header>

      <main className="content">
        {error && (
          <div className="notice">
            <p>{error}</p>
            <p className="notice-sub">
              Chạy <code>python fetch_data.py</code> rồi <code>python analysis.py</code> trong thư mục gốc, sau đó tải lại trang này.
            </p>
          </div>
        )}

        {data && (
          <>
            <section className="meta-row">
              <div className="meta-item">
                <span className="meta-label">Tháng mục tiêu</span>
                <span className="meta-value">{data.target_month}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Cập nhật lúc</span>
                <span className="meta-value">{data.generated_at}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Trọng số</span>
                <span className="meta-value">
                  Mùa vụ {data.weights.seasonal} · Momentum {data.weights.momentum}
                </span>
              </div>
            </section>

            <section className="picks-section">
              <h2>Top 3 tháng này</h2>
              <div className="picks-grid">
                {data.picks.map((p, i) => (
                  <div className="pick-card" key={p.symbol}>
                    <span className="pick-rank">{String(i + 1).padStart(2, '0')}</span>
                    <span className="pick-symbol">
                      {p.symbol} <PriceInfoButton symbol={p.symbol} />
                    </span>
                    <div className="pick-stats">
                      <div className="pick-stat">
                        <span>Mùa vụ (Sharpe)</span>
                        <strong>{p.seasonal_score.toFixed(2)}</strong>
                      </div>
                      <div className="pick-stat">
                        <span>Momentum 3T</span>
                        <PctTag value={p.momentum_score} />
                      </div>
                      <div className="pick-stat">
                        <span>Điểm tổng hợp</span>
                        <strong>{p.combo_score.toFixed(3)}</strong>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <PositionSizer picks={data.picks} targetMonth={data.target_month} />

            <section className="table-section">
              <h2>Toàn bộ xếp hạng (15 mã đầu)</h2>
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Mã</th>
                    <th>Mùa vụ</th>
                    <th>Momentum</th>
                    <th>Điểm tổng hợp</th>
                  </tr>
                </thead>
                <tbody>
                  {data.all_candidates_ranked.map((c, i) => (
                    <tr key={c.symbol} className={i < 3 ? 'row-picked' : ''}>
                      <td>{i + 1}</td>
                      <td className="cell-symbol">{c.symbol} <PriceInfoButton symbol={c.symbol} /></td>
                      <td>{c.seasonal_score.toFixed(2)}</td>
                      <td><PctTag value={c.momentum_score} /></td>
                      <td>{c.combo_score.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <footer className="footnote">
              <p>{data.note}</p>
            </footer>
          </>
        )}

        {history && history.stats && (
          <section className="history-section">
            <h2>Lịch sử &amp; Hiệu quả hệ thống</h2>
            <p className="section-lead">
              Đây là kết quả walk-forward thật — mỗi tháng trong bảng dưới đây, hệ thống
              chỉ dùng dữ liệu ĐẾN TRƯỚC tháng đó để chọn mã, giống hệt như bạn đang dùng
              trực tiếp mỗi tháng vậy, không có yếu tố "biết trước tương lai".
              {history.transaction_cost_pct !== undefined && (
                <> Đã trừ <strong>{history.transaction_cost_pct}%</strong> chi phí (phí môi giới 2 chiều + thuế bán CK) mỗi lần giao dịch.</>
              )}
            </p>

            <div className="stats-grid">
              <div className="stat-box">
                <span className="stat-label">Số tháng đã kiểm chứng</span>
                <span className="stat-value">{history.stats.n_months_tested} tháng ({history.stats.n_years_tested} năm)</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">Vốn (mô phỏng 3tr/tháng)</span>
                <span className="stat-value">{fmtVND(history.stats.total_invested)} → {fmtVND(history.stats.final_balance)}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">Lợi nhuận tổng</span>
                <span className="stat-value"><PctTag value={history.stats.total_return_pct} /></span>
              </div>
              <div className="stat-box">
                <span className="stat-label">CAGR ước tính</span>
                <span className="stat-value"><PctTag value={history.stats.cagr_approx_pct} />/năm</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">Tỷ lệ tháng dương</span>
                <span className="stat-value">{history.stats.win_rate_pct}%</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">Max Drawdown</span>
                <span className="stat-value stat-negative">{history.stats.max_drawdown_pct}%</span>
              </div>
            </div>

            <h3>Đường cong vốn (mô phỏng, bơm {fmtVND(history.inject_per_month)}/tháng)</h3>
            <EquityChart monthlyLog={history.monthly_log} />

            <h3>Phân phối lợi nhuận từng tháng</h3>
            <MonthlyReturnsBar monthlyLog={history.monthly_log} />

            <div className="best-worst-row">
              <div className="bw-box bw-best">
                <span className="bw-label">Tháng tốt nhất</span>
                <span className="bw-month">{history.stats.best_month.label}</span>
                <span className="bw-picks">{history.stats.best_month.picks.join(' · ')}</span>
                <PctTag value={history.stats.best_month.return_pct} />
              </div>
              <div className="bw-box bw-worst">
                <span className="bw-label">Tháng tệ nhất</span>
                <span className="bw-month">{history.stats.worst_month.label}</span>
                <span className="bw-picks">{history.stats.worst_month.picks.join(' · ')}</span>
                <PctTag value={history.stats.worst_month.return_pct} />
              </div>
            </div>

            <h3>Nhật ký từng tháng</h3>
            <table className="history-table">
              <thead>
                <tr>
                  <th>Tháng</th>
                  <th>3 mã đã chọn</th>
                  <th>Kết quả</th>
                  <th>Vốn cộng dồn</th>
                </tr>
              </thead>
              <tbody>
                {[...history.monthly_log]
                  .reverse()
                  .slice(0, showAllHistory ? undefined : 12)
                  .map((m) => (
                    <tr key={m.label}>
                      <td className="cell-symbol">{m.label}</td>
                      <td>{m.picks.join(' · ')}</td>
                      <td><PctTag value={m.return_pct} /></td>
                      <td>{fmtVND(m.balance)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
            {history.monthly_log.length > 12 && (
              <button className="toggle-btn" onClick={() => setShowAllHistory((v) => !v)}>
                {showAllHistory ? 'Thu gọn' : `Xem toàn bộ ${history.monthly_log.length} tháng`}
              </button>
            )}

            <h3>Chiến lược đã qua kiểm chứng gì</h3>
            <ul className="validation-list">
              {history.validation_notes.map((note, i) => (
                <li key={i}>{note}</li>
              ))}
            </ul>
          </section>
        )}

        {!data && !error && <p className="loading">Đang tải…</p>}
      </main>
    </div>
  )
}
