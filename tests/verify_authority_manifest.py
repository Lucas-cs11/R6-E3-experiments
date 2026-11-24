#!/usr/bin/env python3
"""E3-00 archive authority gate; not a scientific acceptance tool."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('artifact_path sha256 version status claim_ids supersedes withdrawal_reason '
          'source_of_truth verified_by verification_command').split()
VALID = {'CURRENT', 'RETRACTED', 'HISTORICAL', 'UNVERIFIED'}
TINA = 'baseline_readonly/e2/runs/tina_cloud_45192651608/merged_candidate_verdicts.csv'
UNIVERSE = 'baseline_readonly/e2/scope/generator_candidate_universe_full.csv'
PROB = 'baseline_readonly/e2/results/probability_a4_21points.csv'
SUMMARY = 'reports/current_evidence_scope.md'


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def path(rel):
    p = ROOT / rel
    need(not Path(rel).is_absolute() and p.resolve().relative_to(ROOT).as_posix() == rel,
         f'noncanonical evidence path: {rel}')
    return p


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def frozen_files():
    return {p.relative_to(ROOT).as_posix() for p in (ROOT / 'baseline_readonly').rglob('*') if p.is_file()}


def render(tina, universe, probability):
    with path(universe).open(newline='') as f:
        population = list(csv.DictReader(f))
    ids = [r['candidate_id'] for r in population if r['static_validity'] == 'VALID_BY_FROZEN_RULE']
    with path(tina).open(newline='') as f:
        rows = list(csv.DictReader(f))
    need(len(ids) == len(set(ids)) and [r['candidate_id'] for r in rows] == ids, 'projection coverage mismatch')
    counts = Counter(r['status'] for r in rows)
    need(counts.keys() <= {'BOUNDED', 'TIMEOUT'}, 'unexpected archived P/T verdict')
    with path(probability).open(newline='') as f:
        points = list(csv.DictReader(f))
    need([int(r['k']) for r in points] == list(range(21)), 'probability grid mismatch')
    for r in points:
        a = 3 + Fraction(int(r['k']), 20)
        need((Fraction(r['a4']), Fraction(r['Pe']), Fraction(r['Gamma'])) ==
             (a, (4-a)/4, (a-2)/4 + 1/(2*(5-a))), 'continuous reference mismatch')
    return (f'# E3 当前证据口径\n\n'
            f'- 结构/范围：冻结 E2 清单 {len(population):,} 行，其中 {len(ids):,} 行符合旧静态规则；不是 E3 正式研究域签署。\n'
            f'- P/T 投影：继承的 E2 总账有 {len(rows):,} 条；{counts["BOUNDED"]:,} 条有界，{counts["TIMEOUT"]:,} 条超时未决。此入口核对覆盖及冻结文件，未在 E3 重放求解器。\n'
            f'- 概率参照：{len(points)} 个等先验连续观测点通过有理数复算；不代表合同概率矩阵。\n'
            f'- 局部、同题定时诊断及经验评价：本清单未为这些类别授予新的 E3 验收。\n'
            f'- 总状态：`NOT_CLOSED`；本检查只处理归档证据权威及当前摘要。\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', type=Path, default=path('contracts/evidence_authority_manifest.csv'))
    ap.add_argument('--summary-inputs', type=Path, default=path('contracts/current_summary_inputs.json'))
    ap.add_argument('--write-summary', action='store_true')
    args = ap.parse_args()
    with args.manifest.open(newline='') as f:
        reader = csv.DictReader(f)
        need(reader.fieldnames == FIELDS, 'authority manifest schema mismatch')
        records = list(reader)
    index = {r['artifact_path']: r for r in records}
    need(len(index) == len(records) and index.keys() == frozen_files(), 'duplicate, missing or extra authority rows')
    for rel, r in index.items():
        need(r['status'] in VALID and r['verified_by'] and r['verification_command'], f'missing authority metadata: {rel}')
        need(r['status'] != 'RETRACTED' or r['withdrawal_reason'].startswith('RETRACTED_DO_NOT_CITE:'), f'missing withdrawal reason: {rel}')
        need(sha(path(rel)) == r['sha256'], f'authority SHA mismatch: {rel}')
    for item in json.loads(path('contracts/input_inventory.json').read_text())['items']:
        rel = item['frozen']
        need(index[rel]['sha256'] == item['sha256'], f'input inventory mismatch: {rel}')
    current = {TINA, UNIVERSE, PROB}
    need({p for p, r in index.items() if r['status'] == 'CURRENT'} == current, 'unexpected CURRENT artifact set')
    inputs = json.loads(args.summary_inputs.read_text())
    for rel in inputs.values():
        need(rel in index and index[rel]['status'] == 'CURRENT', f'CURRENT_SUMMARY_DEPENDENCY_NOT_CURRENT: {rel}')
    need(inputs == {'tina': TINA, 'universe': UNIVERSE, 'probability': PROB}, 'unexpected summary source binding')
    text = render(**inputs)
    if args.write_summary:
        path(SUMMARY).write_text(text)
    need(path(SUMMARY).read_text() == text, 'current summary differs from recomputed source')
    print(json.dumps({'status': 'PASS', 'scope': 'E3-00_AUTHORITY_ONLY', 'rows': len(records),
                      'authority_counts': Counter(r['status'] for r in records)}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise SystemExit(str(exc)) from None
