import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchAppointments, fetchDoctors, fetchHealth, resetDemo } from './api'
import { useCall } from './useCall'
import Appointments from './components/Appointments'
import Doctors from './components/Doctors'
import { PhoneIcon } from './components/Icons'
import Phone from './components/Phone'
import Transcript from './components/Transcript'

const none = () => ({ slots: new Set(), appts: new Set() })

export default function App() {
  const [doctors, setDoctors] = useState([])
  const [appts, setAppts] = useState([])
  const [loading, setLoading] = useState(true)
  const [health, setHealth] = useState(null)
  const [flash, setFlash] = useState(none())
  const prevSlots = useRef(new Map())
  const prevAppts = useRef(new Map())
  const flashTimer = useRef(null)

  const refresh = useCallback(async () => {
    try {
      const [d, a] = await Promise.all([fetchDoctors(), fetchAppointments()])
      const f = none()
      if (prevSlots.current.size) d.forEach((doc) => doc.slots.forEach((s) => { const p = prevSlots.current.get(s.id); if (p && p !== s.state) f.slots.add(s.id) }))
      if (prevAppts.current.size || prevSlots.current.size) a.forEach((x) => { if (prevAppts.current.get(x.id) !== x.status) f.appts.add(x.id) })
      prevSlots.current = new Map(d.flatMap((doc) => doc.slots.map((s) => [s.id, s.state])))
      prevAppts.current = new Map(a.map((x) => [x.id, x.status]))
      setDoctors(d); setAppts(a); setLoading(false)
      if (f.slots.size || f.appts.size) {
        setFlash(f)
        clearTimeout(flashTimer.current)
        flashTimer.current = setTimeout(() => setFlash(none()), 3000)
      }
    } catch { /* backend not up yet */ }
  }, [])

  const call = useCall({ onAppointmentEvent: refresh })
  const inCall = call.state === 'ringing' || call.state === 'connected'

  useEffect(() => { fetchHealth().then(setHealth).catch(() => setHealth({ ok: false })) }, [])
  useEffect(() => {
    refresh()
    const t = setInterval(refresh, inCall ? 2000 : 8000)
    return () => clearInterval(t)
  }, [refresh, inCall])

  const ready = health?.ok && health.gemini_key && health.elevenlabs_key
  const status = !health ? 'Checking…' : !health.ok ? 'Backend offline' : !ready ? 'API keys missing' : 'Agent ready'

  return (
    <div className="app">
      <header className="top">
        <div className="brand">
          <span className="mark" aria-hidden>M</span>
          <div><h1>Meridian</h1><p>Front desk console</p></div>
        </div>
        <div className="top-right">
          <span className={`status ${ready ? 'ok' : 'bad'}`}><i />{status}</span>
          <button className="link" onClick={async () => { await resetDemo(); refresh() }} disabled={inCall}>Reset demo data</button>
          <button className="cta" onClick={call.start} disabled={inCall || !ready}>
            <PhoneIcon width={18} height={18} />{inCall ? 'On call' : 'Try call'}
          </button>
        </div>
      </header>

      <main className="grid">
        <Doctors doctors={doctors} flash={flash} loading={loading} />
        <div className="side">
          <Appointments appts={appts} flash={flash} />
          <Transcript items={call.transcript} interim={call.interim} live={call.state === 'connected'} />
        </div>
      </main>

      <Phone call={call} />
    </div>
  )
}
