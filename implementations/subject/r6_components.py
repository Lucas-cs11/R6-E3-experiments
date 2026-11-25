"""R6 component integration over the existing real-PN replay infrastructure.

Unmodified execution always calls the established implementations.  Optional
source mutations are explicit test-only paths that replace one verified source
line in memory; frozen infrastructure files are never edited.
"""
import inspect

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
}

_LIMITATIONS = {
    'R6-01': 'Concrete strong-time histories plus finite immediate roots; not continuous-domain exhaustion.',
    'R6-02': 'Concrete completion histories and explicit external token; not all possible external environments.',
}


def mutation_patch(mutation_id):
    """Return the auditable one-line source mutation used by regression tests."""
    spec = _MUTATIONS[mutation_id]
    return dict(component_id=spec['component_id'], mutation_id=mutation_id,
                function=spec['function'].__name__, old=spec['old'], new=spec['new'],
                mode='IN_MEMORY_SOURCE_REPLACE')


def _run_source_mutation(mutation_id, model, history):
    spec = _MUTATIONS[mutation_id]
    function = spec['function']
    source = inspect.getsource(function)
    if source.count(spec['old']) != 1:
        raise RuntimeError(f'mutation anchor is not unique: {mutation_id}')
    namespace = dict(function.__globals__)
    exec(compile(source.replace(spec['old'], spec['new']), f'<{mutation_id}>', 'exec'), namespace)
    return namespace[function.__name__](model, history)


def run_case(component_id, model, case, mutation=None):
    """Execute one model-driven case without consulting the independent oracle."""
    kind = case['kind']
    if kind == 'timed':
        if mutation is not None:
            spec = _MUTATIONS[mutation]
            if spec['component_id'] != component_id:
                raise ValueError('component/mutation mismatch')
            return _run_source_mutation(mutation, model, case['history'])
        return replay(model, case['history'])
    if kind == 'mass':
        if mutation is not None:
            raise ValueError('mass mutation is not defined for this component')
        return propagate(model, case['budget'])
    raise ValueError(f'unsupported component case kind: {kind}')


def make_acceptance_record(component_id, case, subject_output, oracle_output,
                           mutation_id, mutation_exit_code):
    """Package the contract-required, inspectable component acceptance fields."""
    trace = (subject_output.get('trace') or subject_output.get('events') or
             subject_output.get('terminals') or [])
    return dict(
        original_case=case,
        new_counterexample=mutation_patch(mutation_id),
        actual_network_trace=trace,
        subject_output=subject_output,
        oracle_output=oracle_output,
        invariant_verdict='COMPONENT_REGRESSION_PASS',
        mutation_patch=mutation_patch(mutation_id),
        mutation_exit_code=mutation_exit_code,
        coverage_limitations=_LIMITATIONS[component_id],
    )
