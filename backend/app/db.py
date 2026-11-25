"""Mock clinic data in SQLite: doctors, generated slots, appointments."""
import random
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import config

DOCTORS = [
    ("Dr. Ananya Sharma", "General Physician"),
    ("Dr. Rohan Mehta", "Cardiologist"),
    ("Dr. Priya Nair", "Dermatologist"),
    ("Dr. Imran Qureshi", "Orthopedic Surgeon"),
    ("Dr. Kavita Rao", "Pediatrician"),
    ("Dr. Sameer Joshi", "ENT Specialist"),
]
TIMES = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30"]
DAYS_AHEAD = 5  # working days of slots kept available


def now():
    return datetime.now(ZoneInfo(config.CLINIC_TZ))


@contextmanager
def conn():
    c = sqlite3.connect(config.DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY, name TEXT NOT NULL, speciality TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS slots (
  id INTEGER PRIMARY KEY, doctor_id INTEGER NOT NULL REFERENCES doctors(id),
  date TEXT NOT NULL, time TEXT NOT NULL, blocked INTEGER NOT NULL DEFAULT 0,
  UNIQUE(doctor_id, date, time));
CREATE TABLE IF NOT EXISTS appointments (
  id INTEGER PRIMARY KEY, slot_id INTEGER NOT NULL REFERENCES slots(id),
  patient_name TEXT NOT NULL, phone TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'booked',
  created_at TEXT NOT NULL, cancelled_at TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_booking_per_slot ON appointments(slot_id) WHERE status='booked';
"""


def init_db():
    with conn() as c:
        c.executescript(SCHEMA)
        if c.execute("SELECT COUNT(*) FROM doctors").fetchone()[0] == 0:
            c.executemany("INSERT INTO doctors(name, speciality) VALUES (?,?)", DOCTORS)
        ensure_slots(c)
        if c.execute("SELECT COUNT(*) FROM appointments").fetchone()[0] == 0:
            seed_demo_appointments(c)


def ensure_slots(c):
    """Create slots for the next working days (idempotent). Some are blocked for realism."""
    today = now().date()
    day, added = today, 0
    doctors = [r["id"] for r in c.execute("SELECT id FROM doctors")]
    while added < DAYS_AHEAD:
        if day.weekday() != 6:  # clinic closed on Sundays
            for d in doctors:
                rnd = random.Random(f"{d}-{day}")
                for t in TIMES:
                    c.execute("INSERT OR IGNORE INTO slots(doctor_id,date,time,blocked) VALUES (?,?,?,?)",
                              (d, day.isoformat(), t, 1 if rnd.random() < 0.3 else 0))
            added += 1
        day += timedelta(days=1)


def seed_demo_appointments(c):
    """A few existing bookings. Phone 9876543210 can be used to try the cancel flow."""
    stamp = now().isoformat(timespec="seconds")
    rows = c.execute("""SELECT s.id FROM slots s WHERE s.blocked=0 AND s.date>?
                        ORDER BY s.date, s.time LIMIT 40""", (now().date().isoformat(),)).fetchall()
    demo = [("Rahul Verma", "9876543210"), ("Neha Kapoor", "9811122233"), ("Arjun Singh", "9899900011")]
    for (name, phone), r in zip(demo, [rows[3], rows[11], rows[19]]):
        c.execute("INSERT INTO appointments(slot_id,patient_name,phone,status,created_at) VALUES (?,?,?,?,?)",
                  (r["id"], name, phone, "booked", stamp))


def reset_appointments():
    with conn() as c:
        c.execute("DELETE FROM appointments")
        seed_demo_appointments(c)


# ------------------------------------------------------------------ queries
def _is_future(date: str, time: str) -> bool:
    return datetime.fromisoformat(f"{date}T{time}").replace(tzinfo=ZoneInfo(config.CLINIC_TZ)) > now()


def fmt_time(t: str) -> str:
    return datetime.strptime(t, "%H:%M").strftime("%I:%M %p").lstrip("0")


def spoken(date: str, time: str) -> str:
    d = datetime.strptime(date, "%Y-%m-%d")
    return f"{d.strftime('%A')} {d.day} {d.strftime('%B')} at {fmt_time(time)}"


def list_doctors_with_slots():
    with conn() as c:
        ensure_slots(c)
        out = []
        for d in c.execute("SELECT * FROM doctors ORDER BY id"):
            slots = []
            for s in c.execute("""SELECT s.*, (SELECT a.id FROM appointments a WHERE a.slot_id=s.id AND a.status='booked') AS appt
                                  FROM slots s WHERE s.doctor_id=? AND s.date>=? ORDER BY s.date, s.time""",
                               (d["id"], now().date().isoformat())):
                if not _is_future(s["date"], s["time"]):
                    continue
                state = "blocked" if s["blocked"] else "booked" if s["appt"] else "open"
                slots.append({"id": s["id"], "date": s["date"], "time": s["time"], "label": fmt_time(s["time"]), "state": state})
            out.append({"id": d["id"], "name": d["name"], "speciality": d["speciality"], "slots": slots})
        return out


def list_appointments():
    with conn() as c:
        rows = c.execute("""SELECT a.id, a.patient_name, a.phone, a.status, a.created_at, a.cancelled_at,
                            s.date, s.time, d.name AS doctor, d.speciality, s.id AS slot_id
                            FROM appointments a JOIN slots s ON s.id=a.slot_id JOIN doctors d ON d.id=s.doctor_id
                            ORDER BY (a.status='booked') DESC, s.date, s.time""").fetchall()
        return [{**dict(r), "label": spoken(r["date"], r["time"])} for r in rows]
