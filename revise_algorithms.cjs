const fs=require('fs');
let s=fs.readFileSync('examlab/algorithms.py','utf8');
s=s.replace(/"""Independent baseline implementations[\s\S]*?"""/, '"""Paper CP-SAT → Great Deluge method and selected mathematical baselines."""');
s=s.replace(/ALGORITHMS = \{[\s\S]*?\n\}/,'ALGORITHMS = {"cp_gd": "CP-SAT → Great Deluge"}');
s=s.slice(0,s.indexOf('def constructive('))+s.slice(s.indexOf('def neighbor('));
s=s.slice(0,s.indexOf('    elif name in ("sa", "ts", "heuristic")'))+s.slice(s.indexOf('    metrics = p.metrics(b.best, capacity)'));
fs.writeFileSync('examlab/algorithms.py',s);
