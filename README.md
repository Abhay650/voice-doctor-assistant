# Voice AI Doctor Appointment Assistant

A voice agent (**Aria**, receptionist at the fictional *Meridian Clinic*) that checks doctor availability, books and
cancels appointments by phone, plus a dashboard to run the call and watch the data change.

| Part | Tech |
|---|---|
| Voice pipeline | **Pipecat** (Python 3.10+), SmallWebRTC transport, Silero VAD |
| STT / TTS | **ElevenLabs** (realtime Scribe STT, Flash v2.5 TTS) |
| LLM | **Google Gemini** (`gemini-2.5-flash`, free quota), with function calling |
| API | FastAPI + SQLite (mock doctors, slots, appointments) |
| Frontend | React + Vite, `@pipecat-ai/client-js` |

## Run it

You need Python 3.10+, Node 18+, a [Gemini key](https://aistudio.google.com/apikey) and an [ElevenLabs key](https://elevenlabs.io/app/settings/api-keys).

```bash
# 1. Backend
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env   -> add both API keys
uvicorn app.main:app --reload --port 8000

# 2. Frontend (second terminal)
cd frontend
npm install
npm run dev                     # open http://localhost:5173
```

VS Code: *Terminal → Run Task → Run all* starts both. Allow microphone access in the browser (Chrome or Edge recommended).
The first call loads the Silero VAD model, so allow a couple of seconds. Tests: `cd backend && python -m unittest tests.test_tools -v`.

## Try it (the flow for the demo video)

1. Click **Try call**. The phone rings, then Aria greets you.
2. *"I need a cardiologist tomorrow."* Aria calls `check_doctor_availability` and offers slots.
3. *"The ten thirty one."* → gives name and phone → Aria reads the number back digit by digit → *"Yes."*
4. `book_appointment` runs. A confirmation card appears in the phone, the slot chip and the appointment row on the dashboard flash.
5. To test cancelling, call again and say the demo number **9876543210** (seeded for Rahul Verma), or the number you just booked with.

**Reset demo data** (top right) restores the seeded appointments.

## How the pipeline works

Browser mic → WebRTC → **Silero VAD** detects when the caller starts and stops talking → **ElevenLabs STT** turns speech
into text → **Gemini** decides what to say or which tool to call → **ElevenLabs TTS** speaks the reply → WebRTC back to
the browser. The three tools are registered on the Gemini service inside the Pipecat pipeline (`backend/app/bot.py`) and
run against SQLite (`app/tools.py`, `app/db.py`).

The phone-number rule is enforced twice: the system prompt tells Aria to read the number back and wait for a yes, and the
tools refuse to run unless `phone_confirmed=true` and the number is a valid 10-digit one. Callers are identified only by
that spoken number. Tool results that change data also send an RTVI server message so the dashboard refreshes at once,
and the phone shows a booking / cancellation card.

```
backend/app
  main.py     FastAPI: /api/doctors, /api/appointments, /api/offer (WebRTC), /api/reset
  bot.py      Pipecat pipeline, system prompt, tool schemas, tool handlers
  tools.py    check_doctor_availability, book_appointment, cancel_appointment
  db.py       SQLite schema, seeded doctors, generated slots
frontend/src
  useCall.js  Pipecat client, call state machine, transcript, timer, audio levels
  components/ Phone (call screen), Waveform, Doctors, Appointments, Transcript
  sounds.js   ring / connect / end tones (WebAudio, no files)
```

Bonus items included: Silero VAD; phone-style call screen (ringing → connected → ended, caller name, timer, mute, end,
transcript inside the phone); live waveform from real audio levels; booking/cancel confirmation card; row and slot
highlight on change; ring, connect, confirm and end sounds; mobile layout (the phone goes full-screen).

## Troubleshooting
- **"API keys missing"** pill: fill `backend/.env` and restart uvicorn.
- **Call fails right away:** check the browser allowed the microphone, and the backend terminal for ElevenLabs / Gemini errors (quota, wrong key).
- **Gemini model not found:** set `GEMINI_MODEL` in `.env` to any current Flash model.
- Slots are generated for the next 5 working days (Sundays closed) each time the server starts.
