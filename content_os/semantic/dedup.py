from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Mapping

# Small, explicit bilingual concept map. It normalizes recurring Fit Biblia concepts,
# not arbitrary language, so it stays inspectable and deterministic.
ALIASES = {
    'farkasehseg': 'ehseg',
    'esti ehseg': 'ehseg',
    'night hunger': 'ehseg',
    'evening hunger': 'ehseg',
    'kreatin': 'creatine',
    'creatine': 'creatine',
    'idozites': 'timing',
    'timing': 'timing',
    'edzes elott': 'preworkout',
    'edzes utan': 'postworkout',
    'before training': 'preworkout',
    'after training': 'postworkout',
    'feherje': 'protein',
    'protein': 'protein',
    'fogyas': 'fatloss',
    'zsirvesztes': 'fatloss',
    'fat loss': 'fatloss',
    'kaloria': 'calorie',
    'energia deficit': 'energydeficit',
    'energiadeficit': 'energydeficit',
    'calorie deficit': 'energydeficit',
    'rendszer': 'system',
    'szokas': 'habit',
    'habit': 'habit',
}

FIELD_WEIGHTS = {'topic': 0.20, 'problem': 0.25, 'core_thesis': 0.40, 'angle': 0.15}

@dataclass(frozen=True)
class DedupResult:
    status: str
    score: float
    field_scores: dict[str, float]
    reason: str


def _ascii(text: str) -> str:
    text = unicodedata.normalize('NFKD', text or '')
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def normalize(text: str) -> str:
    s = _ascii(text)
    # phrase-first replacement prevents token-level loss of meaning
    for phrase in sorted(ALIASES, key=len, reverse=True):
        s = re.sub(rf'\b{re.escape(phrase)}\b', ALIASES[phrase], s)
    return re.sub(r'\s+', ' ', s).strip()


def tokens(text: str) -> set[str]:
    return {t for t in normalize(text).split() if len(t) > 1}


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def compare(candidate: Mapping[str, str], existing: Mapping[str, str]) -> DedupResult:
    field_scores = {field: jaccard(tokens(candidate.get(field, '')), tokens(existing.get(field, ''))) for field in FIELD_WEIGHTS}
    score = sum(field_scores[k] * FIELD_WEIGHTS[k] for k in FIELD_WEIGHTS)

    thesis = field_scores['core_thesis']
    problem = field_scores['problem']
    topic = field_scores['topic']
    angle = field_scores['angle']

    if thesis >= 0.82 and problem >= 0.65 and topic >= 0.50:
        status = 'DUPLICATE'
        reason = 'same semantic thesis/problem/topic'
    elif score >= 0.48 or (thesis >= 0.55 and (problem >= 0.35 or topic >= 0.50)):
        status = 'RELATED'
        reason = 'meaningfully overlapping concept'
    elif 0.36 <= score < 0.48:
        status = 'NEEDS_REVIEW'
        reason = 'borderline semantic overlap'
    else:
        status = 'NEW'
        reason = 'materially different meaning'

    # Same topic with strongly different angle/thesis should not be forced duplicate.
    if status == 'DUPLICATE' and angle < 0.20 and thesis < 0.90:
        status = 'RELATED'
        reason = 'same core area but materially different angle'

    return DedupResult(status=status, score=round(score, 4), field_scores={k: round(v, 4) for k, v in field_scores.items()}, reason=reason)


def best_match(candidate: Mapping[str, str], existing_rows: Iterable[Mapping[str, str]]):
    best = None
    for row in existing_rows:
        result = compare(candidate, row)
        if best is None or result.score > best['result'].score:
            best = {'row': row, 'result': result}
    return best
