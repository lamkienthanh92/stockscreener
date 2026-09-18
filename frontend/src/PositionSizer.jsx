import { useEffect, useState } from 'react'
import { PriceInfoButton } from './PriceChart.jsx'

const LOT_SIZE = 100          // 1 lô HOSE = 100 cổ phiếu
const STORAGE_KEY = 'vn30_allocation_history'

function fmtVND(v) {
  if (v === null || v === undefined || isNaN(v)) return '—'
  return Math.round(v).toLocaleString('vi-VN') + 'đ'
}

function fmtPct(v) {
  if (v === null || v === undefined || isNaN(v)) return '—'
  const sign = v >= 0 ? '+' : ''
  return `${sign}${v.toFixed(1)}%`
}

function loadHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveHistory(list) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
  } catch {
    // localStorage khong kha dung - bo qua im lang
  }
}

export default function PositionSizer({ picks, targetMonth }) {
  const [capital, setCapital] = useState('')
  const [records, setRecords] = useState([])
  const [savedMsg, setSavedMsg] = useState(false)
  const [latestPrices, setLatestPrices] = useState(null)

  useEffect(() => {
    setRecords(loadHistory())
    fetch('/latest_prices.json')
      .then((r) => (r.ok ? r.json() : {}))
      .then(setLatestPrices)
      .catch(() => setLatestPrices({}))
  }, [])

  const capitalNum = Number(capital.replace ? capital.replace(/[^\d]/g, '') : capital) || 0
  const perStock = capitalNum / 3

  const allocations = picks.map((p) => {
    const priceVnd = p.latest_price * 1000
    const rawShares = priceVnd > 0 ? Math.floor(perStock / priceVnd / LOT_SIZE) * LOT_SIZE : 0
    const cost = rawShares * priceVnd
    return { symbol: p.symbol, priceVnd, shares: rawShares, cost }
  })

  const totalCost = allocations.reduce((s, a) => s + a.cost, 0)
  const leftover = capitalNum - totalCost

  const handleRecord = () => {
    if (capitalNum <= 0) return
    const entry = {
      recorded_at: new Date().toISOString(),
      target_month: targetMonth,
      capital: capitalNum,
      allocations,
      leftover,
    }
    const updated = [entry, ...records]
    setRecords(updated)
    saveHistory(updated)
    setSavedMsg(true)
    setTimeout(() => setSavedMsg(false), 2000)
  }

  const handleClear = () => {
    if (!confirm('Xóa toàn bộ lịch sử đã ghi nhận trên máy này?')) return
    setRecords([])
    saveHistory([])
  }

  // Tinh lai/lo HIEN TAI cho 1 ban ghi da luu, dua tren gia moi nhat
  const computePnL = (record) => {
    if (!latestPrices) return null
    let currentValue = 0
    let costBasis = 0
    const detail = record.allocations.map((a) => {
      const curPrice = latestPrices[a.symbol]
      const curVal = curPrice ? curPrice * 1000 * a.shares : null
      if (curVal !== null) currentValue += curVal
      costBasis += a.cost
      return { ...a, curPrice, curVal }
    })
    const pnl = currentValue - costBasis
    const pnlPct = costBasis > 0 ? (pnl / costBasis) * 100 : null
    return { detail, currentValue, costBasis, pnl, pnlPct }
  }

  // Tong loi nhuan CONG DON tren toan bo lich su da ghi nhan
  const totalPnL = records.reduce(
    (acc, r) => {
      const p = computePnL(r)
      if (!p) return acc
      return { cost: acc.cost + p.costBasis, value: acc.value + p.currentValue }
    },
    { cost: 0, value: 0 }
  )
  const totalPnLPct = totalPnL.cost > 0 ? ((totalPnL.value - totalPnL.cost) / totalPnL.cost) * 100 : null

  return (
    <section className="sizer-section">
      <h2>Tính số cổ phiếu cần mua</h2>
      <p className="section-lead">
        Nhập vốn hiện tại — hệ thống chia đều 1/3 cho mỗi mã (đã kiểm chứng là cách phân
        bổ tốt nhất), làm tròn xuống lô 100 cổ phiếu.
      </p>

      <div className="sizer-input-row">
        <label>
          Vốn hiện tại (đ)
          <input
            type="text"
            inputMode="numeric"
            placeholder="VD: 30000000"
            value={capital}
            onChange={(e) => setCapital(e.target.value.replace(/[^\d]/g, ''))}
          />
        </label>
        <span className="sizer-capital-display">
          {capitalNum > 0 ? fmtVND(capitalNum) : ''}
        </span>
      </div>

      {capitalNum > 0 && (
        <>
          <table className="sizer-table">
            <thead>
              <tr>
                <th>Mã</th>
                <th>Giá hiện tại</th>
                <th>Vốn phân bổ (1/3)</th>
                <th>Số cổ phiếu (lô 100)</th>
                <th>Thành tiền</th>
              </tr>
            </thead>
            <tbody>
              {allocations.map((a) => (
                <tr key={a.symbol}>
                  <td className="cell-symbol">
                    {a.symbol} <PriceInfoButton symbol={a.symbol} />
                  </td>
                  <td>{fmtVND(a.priceVnd)}</td>
                  <td>{fmtVND(perStock)}</td>
                  <td>{a.shares.toLocaleString('vi-VN')} cp</td>
                  <td>{fmtVND(a.cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="sizer-summary">
            <span>Tổng đã dùng: <strong>{fmtVND(totalCost)}</strong></span>
            <span>Còn dư (không đủ 1 lô): <strong>{fmtVND(leftover)}</strong></span>
          </div>

          <button className="record-btn" onClick={handleRecord}>
            {savedMsg ? '✓ Đã ghi nhận' : 'Ghi nhận lần mua này'}
          </button>
        </>
      )}

      {records.length > 0 && (
        <div className="sizer-history">
          <div className="sizer-history-head">
            <h3>Lịch sử đã ghi nhận (lưu trên trình duyệt này)</h3>
            <button className="clear-btn" onClick={handleClear}>Xóa lịch sử</button>
          </div>

          {totalPnLPct !== null && (
            <div className="total-pnl-banner">
              <span>Tổng lời/lỗ hiện tại trên toàn bộ vốn đã ghi nhận:</span>
              <span className={`pnl-big ${totalPnLPct >= 0 ? 'pct-up' : 'pct-down'}`}>
                {fmtVND(totalPnL.value - totalPnL.cost)} ({fmtPct(totalPnLPct)})
              </span>
            </div>
          )}

          <table className="history-table">
            <thead>
              <tr>
                <th>Ghi lúc</th>
                <th>Tháng</th>
                <th>Vốn gốc</th>
                <th>Phân bổ</th>
                <th>Giá trị hiện tại</th>
                <th>Lời/Lỗ</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r, i) => {
                const p = computePnL(r)
                return (
                  <tr key={i}>
                    <td>{new Date(r.recorded_at).toLocaleString('vi-VN')}</td>
                    <td className="cell-symbol">{r.target_month}</td>
                    <td>{fmtVND(r.capital)}</td>
                    <td>
                      {r.allocations.map((a) => `${a.symbol} ×${a.shares}`).join(' · ')}
                    </td>
                    <td>{p ? fmtVND(p.currentValue) : '—'}</td>
                    <td>
                      {p && p.pnlPct !== null ? (
                        <span className={p.pnlPct >= 0 ? 'pct-up' : 'pct-down'}>
                          {fmtPct(p.pnlPct)}
                        </span>
                      ) : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
