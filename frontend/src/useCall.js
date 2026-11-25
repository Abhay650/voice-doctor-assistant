import { useCallback, useEffect, useRef, useState } from 'react'
import { PipecatClient } from '@pipecat-ai/client-js'
import { SmallWebRTCTransport } from '@pipecat-ai/small-webrtc-transport'
import { playConfirm, playConnect, playEnd, startRing, stopRing } from './sounds'

const MIN_RING_MS = 1800

/** Owns the Pipecat client, call state machine, transcript, timer and audio levels. */
export function useCall({ onAppointmentEvent }) {
  const [state, setState] = useState('idle') // idle | ringing | connected | ended | error
  const [transcript, setTranscript] = useState([])
  const [interim, setInterim] = useState('')
  const [muted, setMuted] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [speaker, setSpeaker] = useState(null) // 'user' | 'bot' | null
  const [card, setCard] = useState(null)
  const [error, setError] = useState('')
  const levels = useRef({ local: 0, remote: 0 })
  const client = useRef(null)
  const audioEl = useRef(null)
  const lastRole = useRef(null)
  const lastAt = useRef(0)
  const cbRef = useRef(onAppointmentEvent)
  cbRef.current = onAppointmentEvent

  const push = useCallback((role, text) => {
    if (!text || !text.trim()) return
    const now = Date.now()
    setTranscript((prev) => {
      const last = prev[prev.length - 1]
      // merge consecutive chunks from the same speaker into one bubble
      if (last && last.role === role && lastRole.current === role && now - lastAt.current < 6000) {
        return [...prev.slice(0, -1), { ...last, text: `${last.text} ${text}`.replace(/\s+/g, ' ').trim() }]
      }
      return [...prev, { id: now + Math.random(), role, text: text.trim(), at: new Date() }]
    })
    lastRole.current = role; lastAt.current = now
  }, [])

  // call timer
  useEffect(() => {
    if (state !== 'connected') return
    const t = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(t)
  }, [state])

  // dismiss confirmation card
  useEffect(() => {
    if (!card) return
    const t = setTimeout(() => setCard(null), 9000)
    return () => clearTimeout(t)
  }, [card])

  const start = useCallback(async () => {
    if (client.current) return
    setTranscript([]); setInterim(''); setSeconds(0); setMuted(false); setCard(null); setError('')
    lastRole.current = null; levels.current = { local: 0, remote: 0 }
    setState('ringing')
    startRing()
    const began = Date.now()
    if (!audioEl.current) { audioEl.current = new Audio(); audioEl.current.autoplay = true }

    const c = new PipecatClient({
      transport: new SmallWebRTCTransport({ waitForICEGathering: true }),
      enableMic: true,
      enableCam: false,
      callbacks: {
        onTrackStarted: (track, p) => {
          if (track.kind === 'audio' && p && !p.local) {
            audioEl.current.srcObject = new MediaStream([track])
            audioEl.current.play().catch(() => {})
          }
        },
        onUserTranscript: (d) => { if (d.final) { setInterim(''); push('user', d.text) } else setInterim(d.text) },
        onBotOutput: (d) => {
          const t = d.output_type || d.text_type || d.aggregated_by
          if (t === 'word' || t === 'token') return
          push('bot', d.text)
        },
        onUserStartedSpeaking: () => setSpeaker('user'),
        onUserStoppedSpeaking: () => setSpeaker((s) => (s === 'user' ? null : s)),
        onBotStartedSpeaking: () => setSpeaker('bot'),
        onBotStoppedSpeaking: () => setSpeaker((s) => (s === 'bot' ? null : s)),
        onLocalAudioLevel: (l) => { levels.current.local = l },
        onRemoteAudioLevel: (l) => { levels.current.remote = l },
        onServerMessage: (m) => {
          if (m && m.type === 'appointment_event') {
            setCard(m); playConfirm(); cbRef.current && cbRef.current(m)
          }
        },
        onError: (m) => console.error('RTVI error', m),
        onDisconnected: () => {
          stopRing(); client.current = null
          setState((s) => (s === 'error' ? s : 'ended')); setSpeaker(null)
        },
      },
    })
    client.current = c

    try {
      await c.connect({ webrtcRequestParams: { endpoint: '/api/offer' } })
      const wait = Math.max(0, MIN_RING_MS - (Date.now() - began))
      await new Promise((r) => setTimeout(r, wait))
      stopRing(); playConnect(); setState('connected')
    } catch (e) {
      stopRing(); client.current = null
      try { await c.disconnect() } catch { /* ignore */ }
      setError(e?.message || String(e)); setState('error')
    }
  }, [push])

  const end = useCallback(async () => {
    stopRing()
    const c = client.current
    client.current = null
    if (c) { try { await c.disconnect() } catch { /* ignore */ } }
    playEnd(); setState('ended'); setSpeaker(null)
  }, [])

  const toggleMute = useCallback(() => {
    const c = client.current
    if (!c) return
    const next = !muted
    c.enableMic(!next)
    setMuted(next)
  }, [muted])

  const reset = useCallback(() => { setState('idle'); setCard(null) }, [])

  useEffect(() => () => { stopRing(); client.current?.disconnect?.() }, [])

  return { state, transcript, interim, muted, seconds, speaker, card, error, levels, start, end, toggleMute, reset, dismissCard: () => setCard(null) }
}
