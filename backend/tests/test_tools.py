import os
import tempfile
import unittest

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")

from app import db, tools  # noqa: E402


class ToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()

    def test_phone_normalisation(self):
        self.assertEqual(tools.normalize_phone("+91 98765-43210"), "9876543210")
        self.assertIsNone(tools.normalize_phone("12345"))

    def test_full_flow(self):
        av = tools.check_doctor_availability(speciality="cardio")
        self.assertTrue(av["ok"])
        slot = av["doctors"][0]["slots"][0]["slot_id"]
        # must confirm the number first
        r = tools.book_appointment(slot, "9000000001", "Test User", phone_confirmed=False)
        self.assertFalse(r["ok"])
        r = tools.book_appointment(slot, "9000000001", "Test User", phone_confirmed=True)
        self.assertTrue(r["ok"], r)
        # slot now taken
        r2 = tools.book_appointment(slot, "9000000002", "Other", phone_confirmed=True)
        self.assertFalse(r2["ok"])
        # cancel
        self.assertFalse(tools.cancel_appointment("9000000009", True)["ok"])
        c = tools.cancel_appointment("9000000001", True)
        self.assertTrue(c["ok"], c)
        # slot is free again
        self.assertTrue(tools.book_appointment(slot, "9000000003", "Third", phone_confirmed=True)["ok"])

    def test_unknown_speciality(self):
        self.assertFalse(tools.check_doctor_availability(speciality="astrology")["ok"])


if __name__ == "__main__":
    unittest.main()
