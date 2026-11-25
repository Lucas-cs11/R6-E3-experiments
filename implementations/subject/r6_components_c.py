"""R6-08 single entry: exact interval feasibility and optional bound certificates."""
import json
from fractions import Fraction as F

from ap41_intervals import evaluate
from immediate_evidence import canonical
from immediate_metrics import evaluate_word_metrics
from immediate_mass_reference import distribution
from r6_components import make_acceptance_record as _component_acceptance_record


_PATCHES = {
    'LOOSE_UPPER_CERTIFY': dict(
        component_id='R6-08', old='intersect Pe with [0,min(pi0,pi1)]',
        new='certify the raw Pe upper bound without natural-domain intersection'),
    'TRUST_FLAG': dict(
        component_id='R6-08', old='ignore evidence_valid and replay the pinned model/ledger',
        new='accept evidence_valid=True despite MODEL_SHA_MISMATCH'),
}


def mutation_patch(mutation_id):
    return dict(_PATCHES[mutation_id], mutation_id=mutation_id,
                mode='SPECIFIC_R608_SEMANTIC_MUTATION')


def r608_evaluate(data, mutation=None):
    """Run interval feasibility, optional evidence binding, then exact metrics."""
    if mutation not in (None, 'LOOSE_UPPER_CERTIFY', 'TRUST_FLAG'):
        raise ValueError('unknown R6-08 mutation')
    algebraic = evaluate(data)
    if algebraic['status'] != 'CONDITIONAL_ONLY':
        return algebraic

    evidence = data.get('immediate_evidence')
    if evidence is not None:
        metrics = evaluate_word_metrics(
            evidence['model_bytes'].encode('utf-8'), canonical(evidence['ledger']),
            model_sha256=evidence['model_sha256'], budget=evidence['budget'],
            reference=distribution, pi1=data['pi1'], delta=data['delta'])
        if metrics['status'] != 'EXACT_IMMEDIATE_WORD_METRICS':
            if mutation == 'TRUST_FLAG' and data.get('evidence_valid') is True:
                algebraic['certified'] = True
                algebraic['certificate'] = {'status': 'TRUSTED_FLAG'}
                algebraic['trust_flag_used'] = True
                return algebraic
            return dict(status=metrics['status'], certified=False,
                        reason=metrics.get('reason'), certificate=None,
                        algebraic=algebraic)
        bounded_input = dict(data)
        bounded_input['Pe'] = {'low': metrics['Pe'], 'high': metrics['Pe']}
        bounded_input['Gamma'] = {'low': metrics['Gamma'], 'high': metrics['Gamma']}
        algebraic = evaluate(bounded_input)
        algebraic['certificate'] = metrics
        algebraic['certified'] = False

    if mutation == 'LOOSE_UPPER_CERTIFY':
        algebraic['Pe'] = (F(data['Pe']['low']), F(data['Pe']['high']))
        algebraic['status'] = 'CERTIFIED'
        algebraic['certified'] = True
        algebraic['certificate'] = {'status': 'LOOSE_UPPER_CERTIFY'}
    return algebraic


def _acceptance_projection(output):
    """Preserve the complete result in the existing field-level comparator."""
    canonical = json.dumps(output, sort_keys=True, default=str, separators=(',', ':'))
    events = output.get('proof_trace', [])
    certificate = output.get('certificate')
    if isinstance(certificate, dict):
        events = certificate.get('atoms', events)
    return dict(status=output['status'], resolved=canonical, unresolved='0',
                categories=[], frontier=[], events=events)


def make_acceptance_record(component_id, case, subject_output, oracle_output,
                           mutation_id, mutated_output):
    """Reuse the self-computing component comparator without dropping R6-08 fields."""
    proxy_case = dict(kind='mass')
    packed_mutation = (mutated_output if isinstance(mutated_output, Exception)
                       else _acceptance_projection(mutated_output))
    record = _component_acceptance_record(
        'R6-03', proxy_case, _acceptance_projection(subject_output),
        _acceptance_projection(oracle_output), 'R603_DROP_FRONTIER_MASS', packed_mutation)
    record.update(
        original_case=case,
        new_counterexample=mutation_patch(mutation_id),
        subject_output=subject_output,
        oracle_output=oracle_output,
        mutation_patch=mutation_patch(mutation_id),
        coverage_limitations=('Conditional AP41 interval feasibility plus restricted immediate '
                              'word certificates; no general continuous-density certification.'))
    return record
