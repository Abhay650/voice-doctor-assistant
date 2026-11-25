import { useEffect, useRef } from 'react'

const BARS = 34

/** Canvas bars driven by the live mic / bot audio levels from the Pipecat client. */
export default function Waveform({ levels, speaker, active }) {
  const ref = useRef(null)
  const heights = useRef(new Array(BARS).fill(0.05))
  const speakerRef = useRef(speaker)
  speakerRef.current = speaker

  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1
    const w = canvas.clientWidth, h = canvas.clientHeight
    canvas.width = w * dpr; canvas.height = h * dpr
    ctx.scale(dpr, dpr)
    let raf, t = 0
    const draw = () => {
      t += 0.09
      const sp = speakerRef.current
      const raw = sp === 'bot' ? levels.current.remote : sp === 'user' ? levels.current.local : 0
      const amp = active ? Math.min(1, Math.max(raw * 3, sp ? 0.22 : 0.03)) : 0.03
      ctx.clearRect(0, 0, w, h)
      const gap = 4, bw = (w - gap * (BARS - 1)) / BARS
      ctx.fillStyle = sp === 'bot' ? '#8FA5FF' : sp === 'user' ? '#FFFFFF' : 'rgba(255,255,255,.35)'
      for (let i = 0; i < BARS; i++) {
        const envelope = Math.sin((i / (BARS - 1)) * Math.PI) // taller in the middle
        const wobble = 0.55 + 0.45 * Math.sin(t * (1.2 + (i % 5) * 0.35) + i * 0.8)
        const target = 0.05 + amp * envelope * wobble
        heights.current[i] += (target - heights.current[i]) * 0.28
        const bh = Math.max(3, heights.current[i] * h)
        const x = i * (bw + gap), y = (h - bh) / 2
        ctx.beginPath(); ctx.roundRect(x, y, bw, bh, bw / 2); ctx.fill()
      }
      raf = requestAnimationFrame(draw)
    }
    draw()
    return () => cancelAnimationFrame(raf)
  }, [levels, active])

  return <canvas ref={ref} className="wave" aria-label={speaker === 'bot' ? 'Aria is speaking' : speaker === 'user' ? 'You are speaking' : 'Listening'} />
}
