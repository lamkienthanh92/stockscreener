export default function EquityChart({ monthlyLog }) {
  if (!monthlyLog || monthlyLog.length === 0) return null

  const W = 760
  const H = 220
  const PAD = 32

  const balances = monthlyLog.map((m) => m.balance)
  const min = Math.min(...balances)
  const max = Math.max(...balances)
  const range = max - min || 1

  const points = monthlyLog.map((m, i) => {
    const x = PAD + (i / (monthlyLog.length - 1)) * (W - PAD * 2)
    const y = H - PAD - ((m.balance - min) / range) * (H - PAD * 2)
    return [x, y]
  })

  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')

  // duong cham cho dinh cao nhat tung thoi diem (drawdown reference)
  let runningMax = -Infinity
  const peakPoints = monthlyLog.map((m, i) => {
    runningMax = Math.max(runningMax, m.balance)
    const x = PAD + (i / (monthlyLog.length - 1)) * (W - PAD * 2)
    const y = H - PAD - ((runningMax - min) / range) * (H - PAD * 2)
    return [x, y]
  })
  const peakPath = peakPoints.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')

  const firstLabel = monthlyLog[0].label
  const lastLabel = monthlyLog[monthlyLog.length - 1].label

  const fmtVN = (n) =>
    n >= 1e9 ? `${(n / 1e9).toFixed(2)} tỷ` : `${(n / 1e6).toFixed(0)} tr`

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} className="chart-svg" preserveAspectRatio="xMidYMid meet">
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="var(--line)" strokeWidth="1" />
        <path d={peakPath} fill="none" stroke="var(--line)" strokeWidth="1" strokeDasharray="3,3" />
        <path d={path} fill="none" stroke="var(--brass)" strokeWidth="2" />
        {points.length > 0 && (
          <circle cx={points[points.length - 1][0]} cy={points[points.length - 1][1]} r="3.5" fill="var(--brass)" />
        )}
      </svg>
      <div className="chart-axis-labels">
        <span>{firstLabel} · {fmtVN(monthlyLog[0].balance)}</span>
        <span>{lastLabel} · {fmtVN(monthlyLog[monthlyLog.length - 1].balance)}</span>
      </div>
      <p className="chart-caption">Đường nét đứt = đỉnh vốn cao nhất từng đạt (để thấy rõ các đợt sụt giảm)</p>
    </div>
  )
}
