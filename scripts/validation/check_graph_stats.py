#!/usr/bin/env python
"""Quick script to check graph statistics."""
import json
from collections import Counter
from pathlib import Path

graph_path = Path("data/processed/graph/combined_graph.json")
g = json.load(open(graph_path))

print('=== GRAPH STATISTICS ===')
print(f'Total nodes: {len(g["nodes"])}')
print(f'Total edges: {len(g["edges"])}')

types = Counter(n['type'] for n in g['nodes'])
print('\nNode types:')
for t, count in sorted(types.items()):
    print(f'  {t}: {count}')

sources = Counter(n.get('source', 'legacy') for n in g['nodes'])
print('\nSources:')
for s, count in sorted(sources.items()):
    print(f'  {s}: {count}')

# Check FORCE 2020 sample
force_wells = [n for n in g['nodes'] if n.get('source') == 'force2020' and n['type'] == 'las_document']
print(f'\nFORCE 2020 Wells: {len(force_wells)}')
if force_wells:
    sample = force_wells[0]
    print(f'Sample well ID: {sample["id"]}')
    print(f'Sample attributes: {list(sample["attributes"].keys())[:5]}')
