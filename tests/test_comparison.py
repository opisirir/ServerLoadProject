import unittest
from examlab.comparison import comparison_tables


class ComparisonTests(unittest.TestCase):
    def test_missing_runs_and_descriptive_statistics(self):
        def metrics(peak):
            return dict(peak=peak, feasible=True, minutes_above_capacity=0,
                        excess_participant_minutes=0, load_variance=4)
        e = dict(capacity=100, certified_lower_bound=40,
                 reference={**metrics(200), 'feasible': False, 'minutes_above_capacity': 60},
                 summary=[{'algorithm': 'a'}, {'algorithm': 'b'}],
                 runs=[dict(algorithm='a', metrics=metrics(40), runtime_seconds=1),
                       dict(algorithm='a', metrics=metrics(60), runtime_seconds=3),
                       dict(algorithm='a', metrics=None, runtime_seconds=8),
                       dict(algorithm='b', metrics=None, runtime_seconds=2)])
        tables = comparison_tables(e)
        self.assertEqual(tables['impact'][1]['reduction_pct'], 75)
        self.assertEqual(tables['impact'][1]['utilization_pct'], 50)
        self.assertIsNone(tables['impact'][2]['overload_minutes'])
        row = tables['stability'][0]
        self.assertEqual((row['total'], row['feasible'], row['median'], row['runtime']), (3, 2, 50, 4))
        self.assertAlmostEqual(row['std'], 200 ** .5)
        self.assertEqual(tables['quality'][0]['certified'], 1)
        self.assertEqual(tables['quality'][0]['gap'], 0)
