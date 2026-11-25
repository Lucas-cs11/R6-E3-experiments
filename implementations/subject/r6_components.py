"""R6 component integration over the existing real-PN replay infrastructure.

Unmodified execution always calls the established implementations.  Optional
source mutations are explicit test-only paths that replace one verified source
line in memory; frozen infrastructure files are never edited.
"""
import inspect
from collections import defaultdict
from fractions import Fraction as F

from endpoint_closure import close_endpoint
from immediate_mass import propagate
from timed_trace import replay


_MUTATIONS = {
    'R601_PERSIST_MIDDLE_CLOCK': dict(
        component_id='R6-01', function=replay,
        old="keep = (ages.keys() & enabled(mid) & enabled(post)) - {k}",
        new="keep = (ages.keys() & enabled(post)) - {k}"),
    'R602_IGNORE_COMPLETION_WINDOW': dict(
        component_id='R6-02', function=replay,
        old="completed is not None and completed - fault <= bc",
        new="completed is not None"),
    'R603_DROP_FRONTIER_MASS': dict(
        component_id='R6-03', function=propagate, kind='mass',
        old="unresolved = sum((p for *_, p in queue), F(0))",
        new="unresolved = F(0)"),
    # Coarse fail-stop evidence: clearing every endpoint successor is caught.
    'R604_ALL_SUCCESSORS_CLEARED': dict(
        component_id='R6-04', function=close_endpoint, kind='endpoint',
        old="choices = immediate or ready",
        new="choices = []"),
    # Specific misclassification: cutting the horizon while successors are
    # still fireable makes the endpoint look truncated, so the immediate
    # completion branches are silently lost instead of explored.
    'R604_HORIZON_CUT_LOSES_COMPLETION': dict(
        component_id='R6-04', function=replay, kind='endpoint_via_replay',
        old="elif end == ha and not ready:",
        new="elif end == ha:"),
}

_LIMITATIONS = {
    'R6-01': 'Concrete strong-time histories plus finite immediate roots; not continuous-domain exhaustion.',
    'R6-02': 'Concrete completion histories and explicit external token; not all possible external environments.',
    'R6-03': 'Finite immediate BFS and one concrete timed horizon; not a general LSTPN classification.',
    'R6-04': 'Exhaustive zero-delay suffixes for one concrete prefix only; not continuous-schedule exhaustion.',
}


def mutation_patch(mutation_id):
    """Return the auditable one-line source mutation used by regression tests."""
    spec = _MUTATIONS[mutation_id]
    return dict(component_id=spec['component_id'], mutation_id=mutation_id,
                function=spec['function'].__name__, old=spec['old'], new=spec['new'],
                mode='IN_MEMORY_SOURCE_REPLACE')


def _run_source_mutation(mutation_id, *args):
    spec = _MUTATIONS[mutation_id]
    function = spec['function']
    source = inspect.getsource(function)
    if source.count(spec['old']) != 1:
        raise RuntimeError(f'mutation anchor is not unique: {mutation_id}')
    namespace = dict(function.__globals__)
    exec(compile(source.replace(spec['old'], spec['new']), f'<{mutation_id}>', 'exec'), namespace)
    if spec.get('kind') == 'endpoint_via_replay':
        # Run close_endpoint with the mutated replay bound into its namespace,
        # so the wrong horizon classification propagates into endpoint closure.
        mutated_replay = namespace[function.__name__]
        ce_namespace = dict(close_endpoint.__globals__)
        ce_namespace['replay'] = mutated_replay
        ce_source = inspect.getsource(close_endpoint)
        exec(compile(ce_source, '<close_endpoint_via_mutated_replay>', 'exec'), ce_namespace)
        return ce_namespace['close_endpoint'](*args)
    return namespace[function.__name__](*args)


def _classify_noncompletion(result, model):
    predicate = model.get('noncompletion_marking')
    if not predicate:
        return result
    masses = defaultdict(F)
    for event in result['events']:
        if (event['terminal'] == 'DEADLOCK' and
                all(event['marking'].get(p, 0) >= w for p, w in predicate.items())):
            event['terminal'] = 'NON_COMPLETION_TERMINAL'
        if event['terminal']:
            key = (event['hypothesis'], event['terminal'], tuple(event['word']))
            masses[key] += F(event['mass'])
    result['categories'] = [dict(hypothesis=h, terminal=t, word=w, mass=str(p))
                            for (h, t, w), p in sorted(masses.items())]
    return result


def run_case(component_id, model, case, mutation=None):
    """Execute one model-driven case without consulting the independent oracle."""
    kind = case['kind']
    if mutation is not None:
        spec = _MUTATIONS[mutation]
        spec_kind = {'endpoint_via_replay': 'endpoint'}.get(spec.get('kind', 'timed'),
                                                            spec.get('kind', 'timed'))
        if spec['component_id'] != component_id or spec_kind != kind:
            raise ValueError('component/case-kind/mutation mismatch')
        args = ((model, case['history']) if kind == 'timed' else
                (model, case['budget']) if kind == 'mass' else
                (model, case['prefix'], case['budget']))
        return _run_source_mutation(mutation, *args)
    if kind == 'timed':
        return replay(model, case['history'])
    if kind == 'mass':
        return _classify_noncompletion(propagate(model, case['budget']), model)
    if kind == 'endpoint':
        return close_endpoint(model, case['prefix'], case['budget'])
    raise ValueError(f'unsupported component case kind: {kind}')


_TIMED_KEYS = ('terminal', 'outcome', 'first_fault_time', 'completion_time',
               'endpoint_enabled_to_fire')
_MASS_KEYS = ('resolved', 'unresolved', 'categories', 'frontier')


def outputs_match(kind, subject_output, oracle_output):
    """Field-level agreement check used by the acceptance record itself."""
    if subject_output['status'] != oracle_output['status']:
        return False
    if kind == 'timed' and subject_output['status'] == 'REPLAYED_HISTORY':
        return all(subject_output[k] == oracle_output[k] for k in _TIMED_KEYS)
    if kind == 'mass':
        return all(subject_output[k] == oracle_output[k] for k in _MASS_KEYS)
    if kind == 'endpoint':
        simplify = lambda rows: [(tuple(r['suffix']), r['result']['terminal'],
                                  r['result']['outcome']) for r in rows]
        return (subject_output['visited'] == oracle_output['visited']
                and simplify(subject_output['terminals']) == simplify(oracle_output['terminals'])
                and subject_output['pending'] == oracle_output['pending'])
    return True


def outputs_diverged(kind, baseline_output, mutated_output):
    """True when the mutated run observably departs from the baseline."""
    if isinstance(mutated_output, Exception):
        return True
    return not outputs_match(kind, baseline_output, mutated_output)


def make_acceptance_record(component_id, case, subject_output, oracle_output,
                           mutation_id, mutated_output):
    """Package the contract-required, inspectable component acceptance fields.

    The record computes ``subject_matches_oracle`` and ``mutation_detected``
    itself from the supplied outputs; ``mutated_output`` may be the exception
    raised by a mutated run.  It is a recorder with built-in comparison for
    the fields listed in ``outputs_match`` — not a substitute for the wider
    gate suite.
    """
    kind = case['kind']
    subject_matches_oracle = outputs_match(kind, subject_output, oracle_output)
    mutation_detected = outputs_diverged(kind, subject_output, mutated_output)
    trace = (subject_output.get('trace') or subject_output.get('events') or
             subject_output.get('terminals') or [])
    verdict = ('COMPONENT_REGRESSION_PASS' if subject_matches_oracle and mutation_detected
               else 'COMPONENT_REGRESSION_FAIL')
    return dict(
        original_case=case,
        new_counterexample=mutation_patch(mutation_id),
        actual_network_trace=trace,
        subject_output=subject_output,
        oracle_output=oracle_output,
        invariant_verdict=verdict,
        mutation_patch=mutation_patch(mutation_id),
        mutation_detected=mutation_detected,
        mutation_raised=isinstance(mutated_output, Exception),
        coverage_limitations=_LIMITATIONS[component_id],
    )
