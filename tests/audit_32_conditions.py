"""E3-10 stage-3: revalidate historical 32-condition evidence without new PASS.

REAUTHENTICATED is reserved for complete model/path/integration replay.  The
frozen E2 material contains exact certificate arithmetic but not the original
lstpn engine bytes or raw integration traces, so numeric agreement alone can
only produce PARTIAL.  NI or structurally missing inputs are NOT_REAUTHENTICATED.
"""
import csv
from fractions import Fraction
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/e3_10'


def _rows(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def _normalized(decision):
    return {'PASS': 'PASS', 'FAIL': 'FAIL', 'UNKNOWN': 'UNRESOLVED',
            'NI': 'INSUFFICIENT_DATA'}.get(decision, 'INVALID')


def _numeric_decision(row, epsilon, gamma):
    pe_low = float(row['Pe_lower_value'])
    pe_high = float(row['Pe_upper_value'])
    ga_low = float(row['Gamma_lower_value'])
    ga_high = float(row['Gamma_upper_value'])
    if pe_low > epsilon or ga_high < gamma:
        return 'FAIL'
    if pe_high <= epsilon and ga_low >= gamma:
        return 'PASS'
    return 'UNRESOLVED'


def _interval_check(row):
    checks = []
    for prefix, lower, upper, lower_value, upper_value in (
            ('Pe', 'Pe_lower', 'Pe_upper', 'Pe_lower_value', 'Pe_upper_value'),
            ('Gamma', 'Gamma_lower', 'Gamma_upper', 'Gamma_lower_value', 'Gamma_upper_value')):
        low, high = Fraction(row[lower]), Fraction(row[upper])
        if low < 0 or high > 1 or low > high:
            return False, f'{prefix}_INVALID_INTERVAL'
        if float(row[lower_value]) != float(low) or float(row[upper_value]) != float(high):
            return False, f'{prefix}_EXACT_FLOAT_MISMATCH'
    return True, ''


def audit(cert_path, index_path, protocol_path, models_path):
    certificates = _rows(cert_path)
    index = _rows(index_path)
    models = {row['case_id']: row for row in json.loads(Path(models_path).read_text())}
    protocol = json.loads(Path(protocol_path).read_text())
    epsilon, gamma = Fraction(protocol['epsilon']), Fraction(protocol['gamma'])
    if len(certificates) != 32 or len(index) != 32 or len(models) != 32:
        raise ValueError('expected exactly 32 cases in every source')
    if {row['case_id'] for row in certificates} != {row['case_id'] for row in index} != set(models):
        raise ValueError('case identity mismatch across frozen sources')
    output = []
    for row in certificates:
        case_id = row['case_id']
        old_status = _normalized(row['decision'])
        if row['status'] == 'NI':
            output.append(dict(case_id=case_id, old_status=old_status,
                               replay_result_or_gap='MISSING_MODEL_AND_CERTIFICATE_BYTES',
                               new_validity='NOT_REAUTHENTICATED', replay_result='NOT_REPLAYABLE',
                               gap='MODEL_AND_CERTIFICATE_BYTES|ORIGINAL_LSTPN_ENGINE_BYTES|ORIGINAL_PATH_AND_INTEGRATION_LOGS',
                               Pe_lower='', Pe_upper='', Gamma_lower='', Gamma_upper='',
                               risk_check='NOT_APPLICABLE', completion_check='NOT_REPLAYED'))
            continue
        interval_ok, interval_reason = _interval_check(row)
        decision_ok = _numeric_decision(row, float(epsilon), float(gamma)) == old_status
        replay_ok = interval_ok and decision_ok and case_id in models
        stop = row.get('stop', '')
        missing_engine = 'ORIGINAL_LSTPN_ENGINE_BYTES'
        missing_traces = 'ORIGINAL_PATH_AND_INTEGRATION_LOGS'
        gaps = [] if replay_ok else [reason for reason in (interval_reason, 'DECISION_MISMATCH' if not decision_ok else '') if reason]
        if row['status'] == 'NI' or case_id not in models:
            gaps.append('MODEL_AND_CERTIFICATE_BYTES')
        # Current frozen stop states are budget exhaustion, not full replay.
        complete_replay = replay_ok and stop not in ('TIME_BUDGET', 'SPLIT_BUDGET')
        if not complete_replay:
            gaps.extend([missing_engine, missing_traces, 'BUDGET_OR_REPLAY_CHAIN_INCOMPLETE'])
        new_validity = 'REAUTHENTICATED' if complete_replay else 'PARTIAL' if replay_ok else 'NOT_REAUTHENTICATED'
        output.append(dict(
            case_id=case_id,
            old_status=old_status,
            replay_result_or_gap='NUMERIC_INTERVAL_AND_DECISION_REPLAY_MATCH' if replay_ok else 'NOT_REPLAYABLE',
            new_validity=new_validity,
            replay_result='NUMERIC_MATCH' if replay_ok else 'NUMERIC_MISMATCH',
            gap='|'.join(gaps),
            Pe_lower=row['Pe_lower_value'], Pe_upper=row['Pe_upper_value'],
            Gamma_lower=row['Gamma_lower_value'], Gamma_upper=row['Gamma_upper_value'],
            risk_check='MATCH' if decision_ok else 'MISMATCH',
            completion_check='NOT_REPLAYED',
        ))
    old_counts = dict(PASS=0, FAIL=0, UNRESOLVED=0, INSUFFICIENT_DATA=0)
    new_counts = dict(REAUTHENTICATED=0, PARTIAL=0, NOT_REAUTHENTICATED=0)
    for row in output:
        old_counts[row['old_status']] += 1
        new_counts[row['new_validity']] += 1
    return dict(rows=output, old_counts=old_counts, new_counts=new_counts)


def write_outputs(result):
    OUT.mkdir(parents=True, exist_ok=True)
    fields = ['case_id', 'old_status', 'replay_result_or_gap', 'new_validity', 'replay_result',
              'gap', 'Pe_lower', 'Pe_upper', 'Gamma_lower', 'Gamma_upper', 'risk_check',
              'completion_check']
    with (OUT / 'stage3_32condition_audit.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result['rows'])
    csv_path = OUT / 'stage3_32condition_audit.csv'
    csv_path.write_text(csv_path.read_text().replace('\r\n', '\n'))
    old = result['old_counts']
    new = result['new_counts']
    not_reauthenticated = [row['case_id'] for row in result['rows'] if row['new_validity'] == 'NOT_REAUTHENTICATED']
    text = f"""# E3-10 stage-3: 32-condition certificate audit

## Result

- Historical structural outcomes: {old['PASS']} PASS, {old['FAIL']} FAIL, {old['UNRESOLVED']} UNRESOLVED, {old['INSUFFICIENT_DATA']} INSUFFICIENT_DATA.
- New validity: {new['REAUTHENTICATED']} REAUTHENTICATED, {new['PARTIAL']} PARTIAL, {new['NOT_REAUTHENTICATED']} NOT_REAUTHENTICATED.
- Numeric interval and threshold-decision replay matched: 31/32 cases.
- Full model/path/integration replay completed: 0/32 cases.

The three historical PASS cases remain PARTIAL, not new PASS.  Exact Pe/Gamma
interval agreement and threshold-decision agreement do not prove completion
semantics.  The frozen sources do not contain the original LSTPN engine bytes
or raw integration traces, and archived stops include TIME_BUDGET/SPLIT_BUDGET.

## NOT_REAUTHENTICATED

{', '.join(not_reauthenticated)}

303_right is NI in the historical certificate and has no reauthentication path.
It is retained rather than removed or backfilled.  Every other case retains its
numeric replay result, the original stop state, and the engine/path/log gaps.
"""
    (OUT / 'stage3_audit.md').write_text(text)
    return result


def self_test():
    result = audit(
        ROOT / 'baseline_readonly/e2/chapter6/final_model_certificates.csv',
        ROOT / 'baseline_readonly/e2/chapter6/32工况_来源映射索引.csv',
        ROOT / 'baseline_readonly/e2/chapter6/protocol.json',
        ROOT / 'baseline_readonly/e2/chapter6/full_models.json')
    assert result['old_counts'] == {'PASS': 3, 'FAIL': 25, 'UNRESOLVED': 3, 'INSUFFICIENT_DATA': 1}
    assert result['new_counts'] == {'REAUTHENTICATED': 0, 'PARTIAL': 31, 'NOT_REAUTHENTICATED': 1}
    assert len(result['rows']) == 32
    assert all(row['new_validity'] != 'REAUTHENTICATED' for row in result['rows'])
    ni = next(row for row in result['rows'] if row['case_id'] == '303_right')
    assert ni['new_validity'] == 'NOT_REAUTHENTICATED'
    for case_id in ('205_left', '205_right', '405_left'):
        row = next(row for row in result['rows'] if row['case_id'] == case_id)
        assert row['old_status'] == 'PASS' and row['new_validity'] == 'PARTIAL'
        assert row['completion_check'] == 'NOT_REPLAYED'
    write_outputs(result)
    print(json.dumps({'status': 'STAGE3_AUDIT_COMPLETE', **result['new_counts'],
                      'old_counts': result['old_counts']}))


if __name__ == '__main__':
    self_test()
