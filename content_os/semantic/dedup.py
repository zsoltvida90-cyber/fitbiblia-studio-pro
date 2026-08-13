from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Mapping

ALIASES = {
    'farkasehseg': 'ehseg', 'esti ehseg': 'ehseg', 'night hunger': 'ehseg', 'evening hunger': 'ehseg',
    'kreatin': 'creatine', 'creatine': 'creatine', 'idozites': 'timing', 'timing': 'timing',
    'edzes elott': 'preworkout', 'edzes utan': 'postworkout', 'before training': 'preworkout', 'after training': 'postworkout',
    'feherje': 'protein', 'protein': 'protein', 'fogyas': 'fatloss', 'zsirvesztes': 'fatloss', 'fat loss': 'fatloss', 'weight loss': 'fatloss',
    'kaloria deficit': 'energydeficit', 'kaloriadeficit': 'energydeficit', 'energia deficit': 'energydeficit', 'energiadeficit': 'energydeficit',
    'calorie deficit': 'energydeficit', 'caloric deficit': 'energydeficit', 'rendszer': 'system', 'szokas': 'habit', 'habit': 'habit',
    'alapok': 'basics', 'basics': 'basics'
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
    text = ''.join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r'[^a-z0-9\s]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def normalize(text: str) -> str:
    s = _ascii(text)
    s = re.sub(r'\btestsuly csokkent\w*\b', 'fatloss', s)
    s = re.sub(r'\bfogy\w*\b', 'fatloss', s)
    for phrase in sorted(ALIASES, key=len, reverse=True):
        s = re.sub(rf'\b{re.escape(phrase)}\b', ALIASES[phrase], s)
    return re.sub(r'\s+', ' ', s).strip()

def tokens(text: str) -> set[str]:
    return {t for t in normalize(text).split() if len(t) > 1}

def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb: return 1.0
    if not sa or not sb: return 0.0
    return len(sa & sb) / len(sa | sb)

def compare(candidate: Mapping[str, str], existing: Mapping[str, str]) -> DedupResult:
    if not str(candidate.get('core_thesis') or '').strip() or not str(existing.get('core_thesis') or '').strip() or not str(candidate.get('topic') or '').strip() or not str(existing.get('topic') or '').strip():
        return DedupResult('NEEDS_REVIEW', 0.0, {}, 'missing required semantic fields')
    field_scores = {field: jaccard(tokens(candidate.get(field, '')), tokens(existing.get(field, ''))) for field in FIELD_WEIGHTS}
    score = sum(field_scores[k] * FIELD_WEIGHTS[k] for k in FIELD_WEIGHTS)
    thesis, problem, topic, angle = field_scores['core_thesis'], field_scores['problem'], field_scores['topic'], field_scores['angle']
    if thesis >= 0.82 and problem >= 0.65 and topic >= 0.50:
        status, reason = 'DUPLICATE', 'same semantic thesis/problem/topic'
    elif score >= 0.48 or (thesis >= 0.55 and (problem >= 0.35 or topic >= 0.50)):
        status, reason = 'RELATED', 'meaningfully overlapping concept'
    elif 0.36 <= score < 0.48:
        status, reason = 'NEEDS_REVIEW', 'borderline semantic overlap'
    else:
        status, reason = 'NEW', 'materially different meaning'
    if status == 'DUPLICATE' and angle < 0.20 and thesis < 0.90:
        status, reason = 'RELATED', 'same core area but materially different angle'
    return DedupResult(status, round(score, 4), {k: round(v, 4) for k, v in field_scores.items()}, reason)

def best_match(candidate: Mapping[str, str], existing_rows: Iterable[Mapping[str, str]]):
    best = None
    for row in existing_rows:
        result = compare(candidate, row)
        if best is None or result.score > best['result'].score:
            best = {'row': row, 'result': result}
    return best
