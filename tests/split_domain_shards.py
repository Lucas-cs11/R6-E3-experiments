"""Split preregistered E3-07 tasks into N shard files for the full run."""
import csv, json, sys
from pathlib import Path

src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('runs/e3_07/preregistered_tasks.csv')
n = int(sys.argv[2]) if len(sys.argv) > 2 else 64
out = Path(sys.argv[3]) if len(sys.argv) > 3 else Path('runs/e3_07/shards')
out.mkdir(parents=True, exist_ok=True)
rows = list(csv.DictReader(src.open()))
fields = list(rows[0])
shards = [[] for _ in range(n)]
for i, r in enumerate(rows):
    shards[i % n].append(r)
for k, shard in enumerate(shards):
    with (out / f'shard_{k:03d}.csv').open('w', newline='') as h:
        w = csv.DictWriter(h, fieldnames=fields); w.writeheader(); w.writerows(shard)
print(json.dumps({'shards': n, 'tasks': len(rows), 'per_shard': len(shards[0])}))
