const fmtPhone = (p) => (p && p.length === 10 ? `${p.slice(0, 5)} ${p.slice(5)}` : p)

export default function Appointments({ appts, flash }) {
  const booked = appts.filter((a) => a.status === 'booked').length
  return (
    <section className="panel" aria-labelledby="ap-h">
      <header className="panel-head">
        <h2 id="ap-h">Appointments</h2>
        <span className="count">{booked} upcoming</span>
      </header>
      {appts.length === 0 && <p className="empty">No appointments yet.</p>}
      <ul className="appts">
        {appts.map((a) => (
          <li key={a.id} className={`appt ${a.status} ${flash.appts.has(a.id) ? 'flash' : ''}`}>
            <div className="appt-main">
              <b>{a.patient_name}</b>
              <span className="phone-no">+91 {fmtPhone(a.phone)}</span>
            </div>
            <div className="appt-sub">
              <span>{a.doctor}</span>
              <span>{a.label}</span>
            </div>
            <span className={`badge ${a.status}`}>{a.status === 'booked' ? 'Booked' : 'Cancelled'}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
