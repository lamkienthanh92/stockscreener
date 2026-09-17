import { useEffect, useState } from 'react'

function fmtPct(v) {
  if (v === null || v === undefined) return '—'
  const sign = v >= 0 ? '+' : ''
  return `${sign}${v.toFixed(1)}%`
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
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/recommendations.json')
      .then((r) => {
        if (!r.ok) throw new Error('Chưa có file recommendations.json — hãy chạy analysis.py trước.')
        return r.json()
      })
      .then(setData)
      .catch((e) => setError(e.message))
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
                    <span className="pick-symbol">{p.symbol}</span>
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
                      <td className="cell-symbol">{c.symbol}</td>
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

        {!data && !error && <p className="loading">Đang tải…</p>}
      </main>
    </div>
  )
}
