"""The three voice tools. Pure functions returning JSON-serialisable dicts so they are easy to test."""
import re
from datetime import timedelta

from . import db


def normalize_phone(raw) -> str | None:
    """Return a 10-digit number from whatever the STT/LLM produced, or None if it is not valid."""
    digits = re.sub(r"\D", "", str(raw or ""))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits if len(digits) == 10 else None


def spell_phone(phone: str) -> str:
    return " ".join(phone)


def _resolve_date(value):
    v = str(value or "").strip().lower()
    if not v:
        return None
    today = db.now().date()
    if v == "today":
        return today.isoformat()
    if v == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    return v[:10]


def check_doctor_availability(doctor_name: str | None = None, speciality: str | None = None, date: str | None = None) -> dict:
    date = _resolve_date(date)
    q_name, q_spec = (doctor_name or "").lower().strip(), (speciality or "").lower().strip()
    doctors = []
    for d in db.list_doctors_with_slots():
        if q_name and q_name.replace("dr.", "").replace("dr", "").strip() not in d["name"].lower():
            continue
        if q_spec and q_spec not in d["speciality"].lower() and q_spec not in d["name"].lower():
            continue
        slots = [s for s in d["slots"] if s["state"] == "open" and (not date or s["date"] == date)][:6]
        doctors.append({"doctor_name": d["name"], "speciality": d["speciality"], "slots": [
            {"slot_id": s["id"], "date": s["date"], "time": s["label"], "spoken": db.spoken(s["date"], s["time"])} for s in slots]})
    if not doctors:
        return {"ok": False, "error": "No doctor matches that name or speciality.",
                "available_specialities": sorted({d[1] for d in db.DOCTORS}), "available_doctors": [d[0] for d in db.DOCTORS]}
    if not any(d["slots"] for d in doctors):
        return {"ok": True, "doctors": doctors, "note": "No open slots for this request. Offer another date or doctor."}
    return {"ok": True, "doctors": doctors}


def _phone_guard(phone_number, phone_confirmed):
    phone = normalize_phone(phone_number)
    if not phone:
        return None, {"ok": False, "error": "That is not a valid 10-digit phone number. Ask the caller to repeat it."}
    if phone_confirmed is not True:
        return None, {"ok": False, "error": "The number has not been confirmed. Read it back digit by digit "
                      f"({spell_phone(phone)}), wait for the caller to say yes, then call again with phone_confirmed=true."}
    return phone, None


def book_appointment(slot_id: int, phone_number: str, patient_name: str, phone_confirmed: bool = False) -> dict:
    phone, err = _phone_guard(phone_number, phone_confirmed)
    if err:
        return err
    name = (patient_name or "").strip()
    if not name:
        return {"ok": False, "error": "Patient name is missing. Ask the caller for their name."}
    with db.conn() as c:
        s = c.execute("""SELECT s.*, d.name AS doctor, d.speciality FROM slots s JOIN doctors d ON d.id=s.doctor_id
                         WHERE s.id=?""", (slot_id,)).fetchone()
        if not s:
            return {"ok": False, "error": "Unknown slot_id. Use a slot_id returned by check_doctor_availability."}
        if s["blocked"] or not db._is_future(s["date"], s["time"]):
            return {"ok": False, "error": "That slot is not available. Offer other slots."}
        if c.execute("SELECT 1 FROM appointments WHERE slot_id=? AND status='booked'", (slot_id,)).fetchone():
            return {"ok": False, "error": "That slot was just taken. Check availability again."}
        if c.execute("""SELECT 1 FROM appointments a JOIN slots s2 ON s2.id=a.slot_id
                        WHERE a.phone=? AND a.status='booked' AND s2.date=? AND s2.time=?""", (phone, s["date"], s["time"])).fetchone():
            return {"ok": False, "error": "This caller already has an appointment at that time."}
        cur = c.execute("INSERT INTO appointments(slot_id,patient_name,phone,status,created_at) VALUES (?,?,?,?,?)",
                        (slot_id, name, phone, "booked", db.now().isoformat(timespec="seconds")))
        appt_id = cur.lastrowid
    appt = {"appointment_id": appt_id, "patient_name": name, "phone": phone, "doctor": s["doctor"],
            "speciality": s["speciality"], "when": db.spoken(s["date"], s["time"]), "date": s["date"], "time": db.fmt_time(s["time"])}
    return {"ok": True, "appointment": appt, "_event": {"type": "appointment_event", "action": "booked", "appointment": appt}}


def cancel_appointment(phone_number: str, phone_confirmed: bool = False, appointment_id: int | None = None) -> dict:
    phone, err = _phone_guard(phone_number, phone_confirmed)
    if err:
        return err
    with db.conn() as c:
        rows = c.execute("""SELECT a.id, a.patient_name, s.date, s.time, d.name AS doctor, d.speciality
                            FROM appointments a JOIN slots s ON s.id=a.slot_id JOIN doctors d ON d.id=s.doctor_id
                            WHERE a.phone=? AND a.status='booked' ORDER BY s.date, s.time""", (phone,)).fetchall()
        if not rows:
            return {"ok": False, "error": "No upcoming appointment found for this phone number."}
        if appointment_id is not None:
            rows = [r for r in rows if r["id"] == appointment_id]
            if not rows:
                return {"ok": False, "error": "That appointment does not belong to this phone number."}
        elif len(rows) > 1:
            return {"ok": False, "error": "Several appointments found. Ask which one to cancel, then call again with appointment_id.",
                    "appointments": [{"appointment_id": r["id"], "doctor": r["doctor"], "when": db.spoken(r["date"], r["time"])} for r in rows]}
        r = rows[0]
        c.execute("UPDATE appointments SET status='cancelled', cancelled_at=? WHERE id=?",
                  (db.now().isoformat(timespec="seconds"), r["id"]))
    appt = {"appointment_id": r["id"], "patient_name": r["patient_name"], "phone": phone, "doctor": r["doctor"],
            "speciality": r["speciality"], "when": db.spoken(r["date"], r["time"]), "date": r["date"], "time": db.fmt_time(r["time"])}
    return {"ok": True, "cancelled": appt, "_event": {"type": "appointment_event", "action": "cancelled", "appointment": appt}}
