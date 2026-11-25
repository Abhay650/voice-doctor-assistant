import { useEffect, useRef } from 'react'

export default function Transcript({ items, interim, live }) {
  const ref = useRef(null)
  useEffect(() => { ref.current?.scrollTo({ top: ref.current.scrollHeight }) }, [items, interim])
  return (
    <section className="panel transcript" aria-labelledby="tr-h">
      <header className="panel-head">
        <h2 id="tr-h">Live transcript</h2>
        {live && <span className="live"><i />Live</span>}
      </header>
      <div className="tr-body" ref={ref} aria-live="polite">
        {items.length === 0 && !interim && <p className="empty">The conversation appears here once a call starts.</p>}
        {items.map((m) => (
          <p key={m.id} className={`tr ${m.role}`}>
            <span className="who">{m.role === 'bot' ? 'Aria' : 'Caller'}</span>
            <time>{m.at.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time>
            <span className="txt">{m.text}</span>
          </p>
        ))}
        {interim && <p className="tr user ghost"><span className="who">Caller</span><span className="txt">{interim}</span></p>}
      </div>
    </section>
  )
}
