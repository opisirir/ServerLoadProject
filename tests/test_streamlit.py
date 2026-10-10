import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]

class StreamlitTests(unittest.TestCase):
    def test_demo_language_scenario_and_compute_navigation(self):
        app = AppTest.from_file(str(ROOT / 'streamlit_app.py')).run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        self.assertEqual(len(app.metric), 4)
        self.assertEqual(app.metric[2].value, '5,000')
        self.assertEqual(len(app.tabs), 2)
        self.assertEqual(len(app.dataframe[0].value), 4)
        app.sidebar.radio[0].set_value('English').run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.tabs[0].label, 'Comparison')
        app.sidebar.selectbox[1].set_value(0).run()
        self.assertEqual(app.metric[2].value, '500')
        app.sidebar.selectbox[0].set_value('compute').run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.get('form')), 1)
        app.button[0].click().run()
        self.assertEqual(len(app.warning), 1)
        self.assertEqual(len(app.exception), 0)

    def test_compute_from_uploaded_csv(self):
        from io import BytesIO
        from unittest.mock import patch
        upload = BytesIO(b'exam_id,student_count,date,start_time\nA,10,2026-10-08,09:00\nB,20,2026-10-08,10:00\n')
        upload.name = 'small.csv'
        app = AppTest.from_file(str(ROOT / 'streamlit_app.py')).run(timeout=30)
        with patch('streamlit.file_uploader', return_value=upload):
            app.sidebar.selectbox[0].set_value('compute').run()
            app.number_input[0].set_value(1)
            app.number_input[1].set_value(1)
            app.button[0].click().run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        result = app.session_state['computed_report']
        self.assertEqual(result['dataset']['exams'], 2)
        self.assertEqual(len(result['experiments'][0]['runs']), 4)
        self.assertEqual(result['experiments'][0]['capacity'], 5000)

    def test_real_report_session(self):
        import json
        path = ROOT / 'results/real_benchmark.json'
        if not path.exists():
            self.skipTest('Local real-data report is not distributed')
        app = AppTest.from_file(str(ROOT / 'streamlit_app.py'))
        app.session_state['computed_report'] = json.loads(path.read_text(encoding='utf-8'))
        app.run(timeout=30)
        app.sidebar.selectbox[0].set_value('compute').run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        self.assertEqual(app.metric[0].value, '2,219')
        self.assertEqual(len(app.success), 1)

if __name__ == '__main__':
    unittest.main()
