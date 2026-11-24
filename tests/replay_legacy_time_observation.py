"""Reproduce frozen E2 mathematical counterexamples without writing into E2."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'baseline_readonly/e2'


def load(side, filename):
    path = ROOT / side / filename
    s = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(s)
    s.loader.exec_module(module)
    return module, hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sources = {}
    modules = []
    for file in ('r604.py', 'r610.py'):
        pair = []
        for side, filename in [('implementations/subject', file), ('oracles/independent', file.removesuffix('.py') + '_reference.py')]:
            mod, digest = load(side, filename)
            sources[f'{side}/{filename}'] = digest
            pair.append(mod)
        modules.append(pair)
    cases = []
    for name, tf, tc, bc, ha in [('completion_before_fault',3,2,2,5), ('completion_after_HA',1,20,20,5), ('negative_fault_time',-1,1,2,5), ('zero_Bc',1,1,0,5)]:
        data = dict(first_fault_time=tf, completion_time=tc, B_c=bc, H_A=ha)
        subject, oracle = (m.classify(data) for m in modules[0])
        cases.append(dict(id=name, input=data, subject=subject, oracle=oracle, reproduced=subject['outcome']==oracle['outcome']=='COMPLETED_IN_TIME'))
    paths = [dict(id=k, fault=False, completion=2, completion_marking={'done':1}, support=[2,2], enabling_signature='same', external_completion='done', measurable=True, observation='done', omega_c=[['done'],2]) for k in ('p1','p2')]
    data = dict(logical_paths=paths, probability_paths=paths, observation_map={'p1':'done','p2':'done'}, logical_H_psi=1, probability_H_psi=1, post_completion_observed=False, internal_unobservable_deadlock=False)
    subject, oracle = (m.check(data) for m in modules[1])
    reproduced = all(r['status']=='THEOREM_NOT_APPLICABLE' and [k for k,v in r['alignment_checks'].items() if not v]==['observation_injective'] for r in (subject,oracle))
    cases.append(dict(id='same_omega_two_paths_legal_injective_g',input=data,subject=subject,oracle=oracle,reproduced=reproduced))
    print(json.dumps(dict(scope='legacy fixture replay only, not PN-driven acceptance', source_sha256=sources, cases=cases),indent=2))
    return int(not all(c['reproduced'] for c in cases))


if __name__ == '__main__':
    raise SystemExit(main())
