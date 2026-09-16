import unittest

import pandas as pd

from comparison_charts import aligned_curves, concurrent_curve, crop_day, daily_loads, hours_above, prepare_plan


class ComparisonChartTests(unittest.TestCase):
    def plan(self, times, counts):
        return pd.DataFrame({"start": pd.to_datetime(times), "students": counts})

    def test_overlap_midnight_and_simultaneous_end(self):
        p = self.plan(["2023-04-10 23:30", "2023-04-11 00:00", "2023-04-11 00:30"], [100, 200, 50])
        curve = concurrent_curve(p, 60)
        self.assertEqual(curve.tolist(), [100, 300, 250, 50, 0])
        self.assertEqual(hours_above(curve, 200), 1)
        self.assertEqual(hours_above(curve, 300), 0)

    def test_alignment_and_midnight_carry(self):
        a = self.plan(["2023-04-10 23:30"], [100])
        b = self.plan(["2023-04-12 12:00"], [100])
        curves = aligned_curves(a, b, 60)
        cropped = crop_day(curves, "2023-04-11")
        self.assertEqual(cropped.iloc[0]['Before'], 100)
        self.assertEqual(cropped.iloc[-1].sum(), 0)
        self.assertEqual(daily_loads(a, b).sum().tolist(), [100, 100])
        self.assertEqual(curves.iloc[-1].sum(), 0)

    def test_raw_records_are_not_collapsed_and_invalid_dates_rejected(self):
        data = pd.DataFrame({"DERS_KOD": ["A", "A"], "OGR_SAY": [10, 20], "TARIH": ["10.04.2023", "11.04.2023"], "SAAT": ["09:00", "09:00"]})
        result = prepare_plan(data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.start.dt.day.tolist(), [10, 11])
        data.loc[0, 'TARIH'] = 'not a date'
        with self.assertRaises(ValueError):
            prepare_plan(data)


if __name__ == '__main__':
    unittest.main()
