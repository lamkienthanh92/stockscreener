export default function MonthlyReturnsBar({ monthlyLog }) {
  if (!monthlyLog || monthlyLog.length === 0) return null

  const W = 760
  const H = 160
  const PAD_TOP = 10
  const PAD_BOTTOM = 10
  const barGap = 1

  const rets = monthlyLog.map((m) => m.return_pct)
  const maxAbs = Math.max(...rets.map((r) => Math.abs(r)), 1)
  const zeroY = PAD_TOP + (H - PAD_TOP - PAD_BOTTOM) / 2
  const scale = (H - PAD_TOP - PAD_BOTTOM) / 2 / maxAbs

  const barW = (W - barGap * (monthlyLog.length - 1)) / monthlyLog.length

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} className="chart-svg">
        <line x1="0" y1={zeroY} x2={W} y2={zeroY} stroke="var(--line)" strokeWidth="1" />
        {monthlyLog.map((m, i) => {
          const x = i * (barW + barGap)
          const h = Math.abs(m.return_pct) * scale
          const y = m.return_pct >= 0 ? zeroY - h : zeroY
          return (
            <rect
              key={m.label}
              x={x}
              y={y}
              width={Math.max(barW, 0.5)}
              height={Math.max(h, 0.5)}
              fill={m.return_pct >= 0 ? 'var(--up)' : 'var(--down)'}
              opacity="0.85"
            >
              <title>{`${m.label}: ${m.return_pct >= 0 ? '+' : ''}${m.return_pct.toFixed(1)}%`}</title>
            </rect>
          )
        })}
      </svg>
      <p className="chart-caption">
        Mỗi cột = 1 tháng đã test · Đỏ = lãi, Xanh = lỗ (quy ước VN) · Di chuột vào cột để xem chi tiết
      </p>
    </div>
  )
}
