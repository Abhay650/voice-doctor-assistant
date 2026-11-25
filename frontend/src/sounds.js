// Tiny WebAudio sound kit: ring, connect chime, end-call tone. No audio files needed.
let ctx = null
let ringTimer = null

const ac = () => {
  if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)()
  if (ctx.state === 'suspended') ctx.resume()
  return ctx
}

function tone(freq, start, dur, vol = 0.06, type = 'sine') {
  const a = ac()
  const o = a.createOscillator(), g = a.createGain()
  o.type = type; o.frequency.value = freq
  const t = a.currentTime + start
  g.gain.setValueAtTime(0, t)
  g.gain.linearRampToValueAtTime(vol, t + 0.02)
  g.gain.linearRampToValueAtTime(0, t + dur)
  o.connect(g).connect(a.destination)
  o.start(t); o.stop(t + dur + 0.05)
}

export function startRing() {
  stopRing()
  const burst = () => { tone(440, 0, 0.4); tone(480, 0, 0.4); tone(440, 0.55, 0.4); tone(480, 0.55, 0.4) }
  burst()
  ringTimer = setInterval(burst, 2200)
}
export function stopRing() { if (ringTimer) clearInterval(ringTimer); ringTimer = null }
export const playConnect = () => { tone(660, 0, 0.12); tone(880, 0.12, 0.18) }
export const playEnd = () => { tone(480, 0, 0.18, 0.06); tone(360, 0.2, 0.28, 0.06) }
export const playConfirm = () => { tone(784, 0, 0.1, 0.05); tone(1047, 0.1, 0.2, 0.05) }
