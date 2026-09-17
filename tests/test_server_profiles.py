import json
from pathlib import Path
import tempfile
import unittest

from data_loader import load_all_data
from evaluation import evaluate_schedule
from models import Exam, Timeslot
from server_profiles import build_server_config, save_server_profile


class ServerProfileTests(unittest.TestCase):
    def test_default_loader_uses_scenario_three(self):
        data = load_all_data(None, "data/example_planned_schedule.csv", None)
        self.assertEqual(data[6].max_concurrent_students, 3000)
        self.assertTrue(all(t.max_cpu == 48 and t.max_ram == 96 for t in data[5].values()))

    def test_capacity_boundary_for_all_profiles(self):
        for profile, capacity in [("moodle_1", 400), ("moodle_2", 2000), ("moodle_3", 3000)]:
            c = build_server_config(profile)
            slot = Timeslot("T", "2026-07-01", "09:00", "10:00", capacity,
                            c.max_cpu, c.max_ram, c.max_bandwidth, capacity)
            for count, feasible in [(capacity, True), (capacity + 1, False)]:
                metrics = evaluate_schedule({"E": "T"}, {"E": Exam("E", "Exam", count)}, {}, {"T": slot}, c)
                self.assertEqual(metrics["capacity_violations"] == 0, feasible)

    def test_profile_preserves_topology_and_units(self):
        c = build_server_config()
        self.assertEqual((c.max_cpu, c.max_ram, c.max_bandwidth), (48, 96, 1000))
        with tempfile.TemporaryDirectory() as folder:
            save_server_profile(folder, "moodle_3", c)
            saved = json.loads((Path(folder) / "server_profile.json").read_text(encoding="utf-8"))
            self.assertEqual(len(saved["infrastructure"]["nodes"]), 10)
            self.assertEqual(saved["config"]["max_concurrent_students"], 3000)
