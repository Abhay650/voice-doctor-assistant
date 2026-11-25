import { useEffect, useRef } from 'react'
import { CheckIcon, CrossIcon, HangIcon, MicIcon, MicOffIcon } from './Icons'
import Waveform from './Waveform'

const mmss = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

function ConfirmCard({ card, onClose }) {
  const a = card.appointment
  const booked = card.action === 'booked'
  return (
    <div className={`confirm ${booked ? 'is-booked' : 'is-cancelled'}`} role="status">
      <span className="confirm-icon">{booked ? <CheckIcon /> : <CrossIcon />}</span>
      <div className="confirm-body">
        <b>{booked ? 'Appointment booked' : 'Appointment cancelled'}</b>
        <span>{a.doctor} · {a.speciality}</span>
        <span>{a.when}</span>
        <small>Ref #{a.appointment_id} · {a.patient_name}</small>
      </div>
      <button className="confirm-x" onClick={onClose} aria-label="Dismiss"><CrossIcon width={16} height={16} /></button>
    </div>
  )
}

export default function Phone({ call }) {
  const { state, transcript, interim, muted, seconds, speaker, card, error, levels, end, toggleMute, reset, start, dismissCard } = call
  const scroller = useRef(null)
  useEffect(() => { scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: 'smooth' }) }, [transcript, interim, card])
  if (state === 'idle') return null

  return (
    <div className="phone-wrap" role="dialog" aria-label="Call with Aria">
      <div className={`phone phone-${state}`}>
        <div className="notch" />
        <div className="phone-status"><span>{state === 'connected' ? 'Connected' : state === 'ringing' ? 'Calling' : state === 'ended' ? 'Call ended' : 'Call failed'}</span><span className="lte">HD voice</span></div>

        {state === 'ringing' && (
          <div className="screen center">
            <div className="avatar big pulse"><span>A</span></div>
            <h3 className="caller">Aria</h3>
            <p className="sub">Meridian Clinic · Front desk</p>
            <p className="ringing">Ringing<i>.</i><i>.</i><i>.</i></p>
            <div className="controls single"><button className="round end" onClick={end} aria-label="Cancel call"><HangIcon /></button></div>
          </div>
        )}

        {state === 'connected' && (
          <div className="screen">
            <div className="caller-row">
              <div className="avatar"><span>A</span></div>
              <div><h3 className="caller sm">Aria</h3><p className="sub">Meridian Clinic · Front desk</p></div>
              <time className="timer">{mmss(seconds)}</time>
            </div>
            <Waveform levels={levels} speaker={speaker} active />
            <div className="phone-transcript" ref={scroller} aria-live="polite">
              {transcript.length === 0 && <p className="hint">Say hello. Aria is listening.</p>}
              {transcript.map((m) => <div key={m.id} className={`bubble ${m.role}`}>{m.text}</div>)}
              {interim && <div className="bubble user ghost">{interim}</div>}
            </div>
            {card && <ConfirmCard card={card} onClose={dismissCard} />}
            <div className="controls">
              <button className={`round ${muted ? 'on' : ''}`} onClick={toggleMute} aria-pressed={muted} aria-label={muted ? 'Unmute' : 'Mute'}>
                {muted ? <MicOffIcon /> : <MicIcon />}<span>{muted ? 'Unmute' : 'Mute'}</span>
              </button>
              <button className="round end" onClick={end} aria-label="End call"><HangIcon /><span>End</span></button>
            </div>
          </div>
        )}

        {(state === 'ended' || state === 'error') && (
          <div className="screen center">
            <div className="avatar big"><span>A</span></div>
            <h3 className="caller">{state === 'ended' ? 'Call ended' : "Couldn't connect"}</h3>
            {state === 'ended' ? <p className="sub">{mmss(seconds)} · {transcript.length} messages</p> : <p className="sub err">{error}</p>}
            <div className="controls">
              <button className="pill" onClick={start}>Call again</button>
              <button className="pill ghost" onClick={reset}>Close</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
