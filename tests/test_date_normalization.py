import unittest
from datetime import date, datetime

import numpy as np
import pandas as pd

from examlab.data import _normalize_date_series


class DateNormalizationTests(unittest.TestCase):
    def test_datetime_column_under_strict_numpy_errors(self):
        values = pd.Series(pd.to_datetime(["2026-11-16", None, "2026-01-02"]))
        with np.errstate(all="raise"):
            actual = _normalize_date_series(values)
        self.assertEqual(actual.tolist(), ["2026-11-16", "", "2026-01-02"])

    def test_mixed_excel_serials_dates_and_invalid_values(self):
        values = pd.Series([
            date(2026, 11, 16), datetime(2026, 11, 17), 46342,
            "46342.5", "16.11.2026", "2026-01-02", None, "invalid", 1e300,
        ], index=range(10, 19), dtype=object)
        with np.errstate(all="raise"):
            actual = _normalize_date_series(values)
        self.assertEqual(actual.tolist(), [
            "2026-11-16", "2026-11-17", "2026-11-16", "2026-11-16",
            "2026-11-16", "2026-01-02", "", "invalid", "1e+300",
        ])
        self.assertTrue(actual.index.equals(values.index))


if __name__ == "__main__":
    unittest.main()
