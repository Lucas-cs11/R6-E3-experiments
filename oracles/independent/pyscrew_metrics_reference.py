"""Independent classification metrics with exact ranking and clipping rules."""
from collections import defaultdict
from fractions import Fraction as F
import math


def auroc(y_true, probabilities):
    """Rank-sum AUROC with average ranks for ties; None on one-class samples."""
    positives = sum(y_true)
    negatives = len(y_true) - positives
    if not positives or not negatives:
        return None
    ordered = sorted(zip(probabilities, y_true), key=lambda item: item[0])
    positive_rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        average_rank = (index + 1 + end) / 2
        positive_rank_sum += average_rank * sum(label for _, label in ordered[index:end])
        index = end
    return (positive_rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def brier(y_true, probabilities):
    if not y_true:
        return None
    return sum((p - y) ** 2 for y, p in zip(y_true, probabilities)) / len(y_true)


def nll(y_true, probabilities, epsilon=1e-12):
    if not y_true:
        return None
    losses = []
    for y, p in zip(y_true, probabilities):
        p = min(1 - epsilon, max(epsilon, p))
        losses.append(-math.log(p if y else 1 - p))
    return sum(losses) / len(losses)


def balanced_accuracy(y_true, probabilities, threshold=0.5):
    positives = sum(y_true)
    negatives = len(y_true) - positives
    if not positives or not negatives:
        return None
    tp = sum(y and p >= threshold for y, p in zip(y_true, probabilities))
    tn = sum(not y and p < threshold for y, p in zip(y_true, probabilities))
    return (tp / positives + tn / negatives) / 2


def risk_coverage(y_true, probabilities, tolerances=(0, 0.1, 0.15, 0.25, 0.5)):
    """Coverage/error at max(p,1-p)>=1-delta, with risk on covered IDs."""
    if not y_true:
        return []
    rows = []
    for delta in tolerances:
        covered = [(y, p) for y, p in zip(y_true, probabilities)
                   if max(p, 1 - p) >= 1 - delta]
        errors = sum(y != (p >= 0.5) for y, p in covered)
        rows.append(dict(delta=delta, covered=len(covered),
                         coverage=len(covered) / len(y_true),
                         risk=errors / len(covered) if covered else None,
                         error_count=errors))
    return rows


def classification_metrics(y_true, probabilities):
    return dict(auroc=auroc(y_true, probabilities), brier=brier(y_true, probabilities),
                nll=nll(y_true, probabilities),
                balanced_accuracy=balanced_accuracy(y_true, probabilities),
                risk_coverage=risk_coverage(y_true, probabilities))


def stratified_metrics(records):
    """Compute identical metrics for every class/side/completion stratum."""
    groups = defaultdict(list)
    for record in records:
        for kind, field in (('class', 'class'), ('side', 'side'),
                            ('completion_status', 'completion_status')):
            groups[kind, record[field]].append(record)
    output = {}
    for (kind, value), group in sorted(groups.items()):
        y = [row['y_true'] for row in group]
        output[kind] = output.get(kind, {})
        output[kind][value] = classification_metrics(y, [row['probability'] for row in group])
    return output
