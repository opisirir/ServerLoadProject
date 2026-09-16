import tempfile
import unittest
from pathlib import Path

import pandas as pd

from data_loader import load_all_data
from data_validator import validate_data


class OvernightSlotTests(unittest.TestCase):
    def test_generated_end_dates_and_explicit_invalid_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.csv"
            pd.DataFrame({
                "exam_id": ["A", "B", "C"], "student_count": [100, 200, 300],
                "date": ["2026-12-31"] * 3, "start_time": ["09:00", "22:00", "23:00"],
            }).to_csv(path, index=False)
            data = load_all_data(None, str(path), None)
            records, exams, slots = data[:3]
            self.assertEqual(slots.end_date.tolist(), ["2026-12-31", "2027-01-01", "2027-01-01"])
            self.assertEqual(slots.end_time.tolist(), ["11:00", "00:00", "01:00"])
            self.assertEqual(validate_data(records, exams, slots, tmp)["errors"], [])
            # An explicitly supplied backwards interval must still be rejected.
            invalid = slots.iloc[:1].drop(columns="end_date").copy()
            invalid["end_time"] = "08:00"
            self.assertTrue(validate_data(records, exams, invalid, tmp)["errors"])


if __name__ == "__main__":
    unittest.main()
