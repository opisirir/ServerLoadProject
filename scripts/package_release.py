"""Build a clean source distribution without private data or Git history."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
files = [ROOT / name for name in ['README.md', 'requirements.txt', 'main.py', 'streamlit_app.py', '.gitignore', '.gitattributes']]
for folder in ['web', 'examlab', 'tests', 'scripts', '.github', '.streamlit', 'docs']:
    files.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc'] and p.name not in ['.DS_Store', 'secrets.toml'])
output = ROOT / 'dist/ExamFlow-publication.zip'
output.parent.mkdir(exist_ok=True)
with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
    for path in sorted(set(files)):
        archive.write(path, path.relative_to(ROOT))
print(output)
