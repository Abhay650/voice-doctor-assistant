import { useMemo, useState } from 'react'

const dayLabel = (iso) => {
  const d = new Date(`${iso}T00:00:00`)
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const diff = Math.round((d - today) / 86400000)
  const wk = d.toLocaleDateString('en-IN', { weekday: 'short' })
  return { top: diff === 0 ? 'Today' : diff === 1 ? 'Tomorrow' : wk, bottom: d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) }
}

export default function Doctors({ doctors, flash, loading }) {
  const dates = useMemo(() => [...new Set(doctors.flatMap((d) => d.slots.map((s) => s.date)))].sort(), [doctors])
  const [picked, setPicked] = useState(null)
  const date = picked && dates.includes(picked) ? picked : dates[0]

  return (
    <section className="panel doctors" aria-labelledby="doc-h">
      <header className="panel-head">
        <h2 id="doc-h">Doctors</h2>
        <div className="days" role="tablist" aria-label="Day">
          {dates.map((iso) => {
            const l = dayLabel(iso)
            return (
              <button key={iso} role="tab" aria-selected={iso === date} className={`day ${iso === date ? 'on' : ''}`} onClick={() => setPicked(iso)}>
                <b>{l.top}</b><span>{l.bottom}</span>
              </button>
            )
          })}
        </div>
      </header>
      {loading && <p className="empty">Loading…</p>}
      <ul className="doc-list">
        {doctors.map((d) => {
          const slots = d.slots.filter((s) => s.date === date && s.state !== 'blocked')
          const open = slots.filter((s) => s.state === 'open').length
          return (
            <li key={d.id} className="doc">
              <div className="doc-who">
                <h3>{d.name}</h3>
                <p>{d.speciality}</p>
              </div>
              <div className="slots">
                {slots.length === 0 && <span className="none">No slots</span>}
                {slots.map((s) => (
                  <span key={s.id} className={`slot ${s.state} ${flash.slots.has(s.id) ? 'flash' : ''}`} title={s.state === 'open' ? 'Available' : 'Booked'}>{s.label}</span>
                ))}
              </div>
              <span className="open-count">{open} open</span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
