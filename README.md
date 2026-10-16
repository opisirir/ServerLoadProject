# ExamFlow: A Capacity-Constrained Exam Timetabling System

Research companion for **Algorithmic Exam Timetabling to Prevent Server Crash in Cloud-Based Learning Management Systems**.

## Run

Python 3.11 is recommended.

```sh
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Open http://localhost:8501. Download the example workbook, upload exam data, run a comparison, and download the selected optimized schedule as Excel. Each Excel export includes reference/optimized start times, end times, and experiment details.

## Example data and results

`web/data/Anonymized_Example_data.xlsx` is the user-supplied anonymized research dataset, distributed unchanged. It contains 2,219 records and 144,467 exam enrollments (not unique students). All supplied records are included; dates span March 28–June 12, 2023. The default report is a newly computed experiment on this file, not a claim to reproduce the exact values in the manuscript's earlier runs. A 10-day filtered analysis requires explicitly filtered input.

```sh
python main.py --input web/data/Anonymized_Example_data.xlsx --scenario scenario_3 --seconds 15 --seeds 42,43,44 --output web/data/benchmark.json
```

Default capacity: 5,000; exam duration: 60 minutes. Exams remain whole. Individual student conflicts are not modeled. CBC goal programming is an equivalent objective reformulation in this implementation; its repeated runs are not independent randomized trials. See `docs/mathematical_comparison.md` for model details.

## Publication

- **GitHub Pages:** the existing workflow publishes only `web/`. This version displays results, accepts report uploads, and exports Excel in the browser; it cannot execute Python optimization.
- **Streamlit:** deploy `streamlit_app.py` with Python 3.11 and `requirements.txt` to run new optimizations.
- `python scripts/package_release.py` creates a clean publication ZIP with an explicit file allowlist. Private data, local outputs, virtual environments, and Git history are excluded.

The current work prepares publication assets; deployment is a separate step. Previously committed private files may remain in Git history; the clean ZIP contains no history.

## Research-use notice

This academic research prototype may not suit every examination timetable. Validate outputs against institutional requirements before use. No warranty of service continuity, crash prevention, or fitness for a particular purpose is provided. To the extent permitted by applicable law, developers and researchers disclaim liability for damages arising from use. Liability that cannot legally be excluded remains unaffected.

## Verification

```sh
python -m unittest discover -s tests
node --test tests/test_web.cjs
```
