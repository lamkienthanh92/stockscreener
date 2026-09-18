import { useEffect, useState } from 'react'

let priceHistoryCache = null

function fetchPriceHistory() {
  if (priceHistoryCache) return Promise.resolve(priceHistoryCache)
  return fetch('/price_history.json')
    .then((r) => (r.ok ? r.json() : {}))
    .then((data) => {
      priceHistoryCache = data
      return data
    })
}

function MiniLineChart({ series }) {
  if (!series || series.length < 2) return <p className="chart-empty">Không đủ dữ liệu để vẽ.</p>

  const W = 640
  const H = 200
  const PAD = 28

  const closes = series.map((p) => p.c)
  const min = Math.min(...closes)
  const max = Math.max(...closes)
  const range = max - min || 1

  const points = series.map((p, i) => {
    const x = PAD + (i / (series.length - 1)) * (W - PAD * 2)
    const y = H - PAD - ((p.c - min) / range) * (H - PAD * 2)
    return [x, y]
  })
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')

  const first = series[0]
  const last = series[series.length - 1]
  const changePct = ((last.c - first.c) / first.c) * 100
  const up = changePct >= 0

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="chart-svg">
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="var(--line)" strokeWidth="1" />
        <path d={path} fill="none" stroke={up ? 'var(--up)' : 'var(--down)'} strokeWidth="1.8" />
        <circle cx={points[points.length - 1][0]} cy={points[points.length - 1][1]} r="3" fill={up ? 'var(--up)' : 'var(--down)'} />
      </svg>
      <div className="chart-axis-labels">
        <span>{first.t} · {first.c.toFixed(1)}</span>
        <span className={up ? 'pct-up' : 'pct-down'}>
          {up ? '+' : ''}{changePct.toFixed(1)}% từ đầu kỳ
        </span>
        <span>{last.t} · {last.c.toFixed(1)}</span>
      </div>
    </div>
  )
}

export function PriceInfoButton({ symbol }) {
  const [open, setOpen] = useState(false)
  const [series, setSeries] = useState(null)

  const handleOpen = () => {
    setOpen(true)
    if (!series) {
      fetchPriceHistory().then((all) => setSeries(all[symbol] || []))
    }
  }

  return (
    <>
      <button className="info-btn" onClick={handleOpen} title={`Xem biểu đồ giá ${symbol}`}>
        !
      </button>
      {open && (
        <div className="modal-backdrop" onClick={() => setOpen(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <span className="modal-symbol">{symbol}</span>
              <button className="modal-close" onClick={() => setOpen(false)}>×</button>
            </div>
            {series ? <MiniLineChart series={series} /> : <p className="loading">Đang tải…</p>}
          </div>
        </div>
      )}
    </>
  )
}
