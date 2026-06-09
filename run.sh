#!/bin/bash
# Show results from the latest benchmark run
latest=$(ls -t results/ | head -1)
if [ -z "$latest" ]; then
  echo "No results found"
  exit 1
fi
echo "Results: results/$latest"
python3 -c "
import json
with open('results/$latest/results.json') as f:
    data = json.load(f)
for r in data['results']:
    t = r['tokens']
    total = t['total'] if t['total'] else 0
    cost = r['cost_usd'] if r['cost_usd'] else 0
    elapsed = r['result']['elapsed_ms'] / 1000
    score = r['scoring'].get('final_score', '?')
    print(f\"{r['provider']:10} {r['model']:20} tokens={total:>10}  cost=\${cost:.4f}  elapsed={elapsed:.1f}s  score={score}\")
"
