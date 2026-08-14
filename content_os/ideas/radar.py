from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Iterable, Mapping, Sequence

try:
    from content_os.semantic.dedup import compare
except ImportError:  # pragma: no cover - allows direct script/test loading
    from semantic.dedup import compare

IDEA_INBOX_COLUMNS = [
    'idea_id','created_at','source_type','source_ref','title','topic_domain','subtopic','persona','problem',
    'proposed_angle','why_now','evidence_readiness','novelty_score','practical_value_score','brand_fit_score',
    'timeliness_score','health_risk_tier','duplicate_status','status','human_decision','promoted_master_id','notes',
    'scope_class','proposed_core_thesis','priority_score','similar_master_ids','decision_reason',
]

CORE_DOMAINS = {'TRAINING','NUTRITION','MINDSET_BEHAVIOR'}
ADJACENT_DOMAINS = {'RECOVERY','HEALTH_WELLBEING','PERFORMANCE','LIFE_SYSTEMS'}
VALID_SCOPE = {'CORE','ADJACENT','OUT_OF_SCOPE'}
VALID_RISK = {'TIER_1','TIER_2','TIER_3'}
VALID_EVIDENCE = {'KNOWN_APPROVED','REUSABLE_RESEARCH','RESEARCH_NEEDED','CONTESTED','UNSUPPORTED','UNKNOWN'}
VALID_DECISIONS = {'SELECT','DEFER','REJECT','RESEARCH_MORE'}

EVIDENCE_SCORE = {
    'KNOWN_APPROVED': 100.0,
    'REUSABLE_RESEARCH': 85.0,
    'RESEARCH_NEEDED': 55.0,
    'UNKNOWN': 35.0,
    'CONTESTED': 20.0,
    'UNSUPPORTED': 0.0,
}
RISK_PENALTY = {'TIER_1': 0.0, 'TIER_2': 8.0, 'TIER_3': 18.0}
DUPLICATE_PENALTY = {'NEW': 0.0, 'RELATED': 8.0, 'NEEDS_REVIEW': 12.0, 'DUPLICATE': 35.0}

TIER3_TERMS = {
    'diagnosis','diagnózis','medication','gyógyszer','gyogyszer','eating disorder','evészavar','eveszavar',
    'anorexia','bulimia','suicide','öngyilkosság','ongyilkossag','psychiatric','pszichiátriai','pszichiatriai',
    'injury treatment','sérülés kezelése','serules kezelese','cure','gyógyít','gyogyit',
}
TIER2_TERMS = {
    'blood pressure','vérnyomás','vernyomas','blood glucose','vércukor','vercukor','cholesterol','koleszterin',
    'diabetes','cukorbetegség','cukorbetegseg','biomarker','cardiovascular','kardiovaszkuláris','kardiovaszkularis',
    'supplement safety','kiegészítő biztonság','kiegeszito biztonsag','supplement efficacy','kiegészítő hatásosság',
    'kiegeszito hatasossag','hormone','hormon',
}

@dataclass(frozen=True)
class RadarIdea:
    idea_id: str
    created_at: str
    source_type: str
    source_ref: str
    title: str
    topic_domain: str
    subtopic: str
    persona: str
    problem: str
    proposed_angle: str
    why_now: str
    evidence_readiness: str
    novelty_score: float
    practical_value_score: float
    brand_fit_score: float
    timeliness_score: float
    health_risk_tier: str
    duplicate_status: str
    status: str
    human_decision: str
    promoted_master_id: str
    notes: str
    scope_class: str
    proposed_core_thesis: str
    priority_score: float
    similar_master_ids: str
    decision_reason: str

    def to_row(self) -> list[object]:
        return [getattr(self, c) for c in IDEA_INBOX_COLUMNS]


def _ascii(text: str) -> str:
    text = unicodedata.normalize('NFKD', text or '')
    return ''.join(ch for ch in text if not unicodedata.combining(ch)).lower()


def _clamp_score(value: object, default: float = 50.0) -> float:
    if value in (None, ''):
        return default
    try:
        return round(max(0.0, min(100.0, float(value))), 1)
    except (TypeError, ValueError):
        return default


def infer_scope(topic_domain: str, explicit: str = '') -> str:
    explicit = str(explicit or '').strip().upper()
    if explicit in VALID_SCOPE:
        return explicit
    domain = str(topic_domain or '').strip().upper()
    if domain in CORE_DOMAINS:
        return 'CORE'
    if domain in ADJACENT_DOMAINS:
        return 'ADJACENT'
    return 'OUT_OF_SCOPE'


def infer_risk(candidate: Mapping[str, object]) -> str:
    explicit = str(candidate.get('health_risk_tier') or '').strip().upper()
    if explicit in VALID_RISK:
        return explicit
    haystack = _ascii(' '.join(str(candidate.get(k) or '') for k in ('title','topic_domain','subtopic','problem','proposed_angle','proposed_core_thesis')))
    if any(_ascii(term) in haystack for term in TIER3_TERMS):
        return 'TIER_3'
    if any(_ascii(term) in haystack for term in TIER2_TERMS):
        return 'TIER_2'
    return 'TIER_1'


def _semantic_row(candidate: Mapping[str, object]) -> dict[str, str]:
    return {
        'topic': str(candidate.get('topic_domain') or candidate.get('topic') or ''),
        'problem': str(candidate.get('problem') or ''),
        'core_thesis': str(candidate.get('proposed_core_thesis') or candidate.get('core_thesis') or ''),
        'angle': str(candidate.get('proposed_angle') or candidate.get('angle') or ''),
    }


def _existing_semantic_row(row: Mapping[str, object]) -> dict[str, str]:
    return {
        'topic': str(row.get('topic') or row.get('topic_domain') or ''),
        'problem': str(row.get('problem') or ''),
        'core_thesis': str(row.get('core_thesis') or row.get('proposed_core_thesis') or ''),
        'angle': str(row.get('angle') or row.get('proposed_angle') or ''),
    }


def dedup_against(candidate: Mapping[str, object], existing_rows: Iterable[Mapping[str, object]]) -> tuple[str, list[str], float, str]:
    semantic_candidate = _semantic_row(candidate)
    if not semantic_candidate['topic'] or not semantic_candidate['core_thesis']:
        return 'NEEDS_REVIEW', [], 0.0, 'provisional thesis/topic missing; semantic dedup cannot be trusted'
    best_status, best_score, best_reason = 'NEW', 0.0, 'no semantic neighbors'
    similar_ids: list[str] = []
    severity = {'NEW':0,'NEEDS_REVIEW':1,'RELATED':2,'DUPLICATE':3}
    for row in existing_rows:
        result = compare(semantic_candidate, _existing_semantic_row(row))
        row_id = str(row.get('master_id') or row.get('idea_id') or row.get('id') or '').strip()
        if result.status in {'RELATED','DUPLICATE','NEEDS_REVIEW'} and row_id:
            similar_ids.append(row_id)
        if result.score > best_score or (result.score == best_score and severity[result.status] > severity[best_status]):
            best_status, best_score, best_reason = result.status, result.score, result.reason
    return best_status, sorted(set(similar_ids))[:8], round(best_score,4), best_reason


def calculate_priority(candidate: Mapping[str, object], evidence_readiness: str, risk: str, duplicate_status: str, scope: str) -> float:
    novelty = _clamp_score(candidate.get('novelty_score'))
    practical = _clamp_score(candidate.get('practical_value_score'))
    brand_fit = _clamp_score(candidate.get('brand_fit_score'))
    timeliness = _clamp_score(candidate.get('timeliness_score'))
    base = 0.15*novelty + 0.25*practical + 0.25*brand_fit + 0.15*timeliness + 0.20*EVIDENCE_SCORE[evidence_readiness]
    score = base - RISK_PENALTY[risk] - DUPLICATE_PENALTY.get(duplicate_status, 12.0)
    if scope == 'ADJACENT':
        score -= 4.0
    elif scope == 'OUT_OF_SCOPE':
        score = 0.0
    return round(max(0.0, min(100.0, score)), 1)


def next_idea_id(existing_ids: Sequence[str], now: datetime) -> str:
    prefix = f'IDEA-{now:%Y%m%d}-'
    nums=[]
    for raw in existing_ids:
        m=re.fullmatch(re.escape(prefix)+r'(\d{3})', str(raw or ''))
        if m: nums.append(int(m.group(1)))
    return f'{prefix}{(max(nums, default=0)+1):03d}'


def triage_candidate(candidate: Mapping[str, object], *, idea_id: str, now: datetime, existing_rows: Iterable[Mapping[str, object]] = ()) -> RadarIdea:
    evidence = str(candidate.get('evidence_readiness') or 'UNKNOWN').strip().upper()
    if evidence not in VALID_EVIDENCE:
        evidence = 'UNKNOWN'
    scope = infer_scope(str(candidate.get('topic_domain') or ''), str(candidate.get('scope_class') or ''))
    risk = infer_risk(candidate)
    duplicate_status, similar_ids, overlap_score, overlap_reason = dedup_against(candidate, existing_rows)
    priority = calculate_priority(candidate, evidence, risk, duplicate_status, scope)

    if scope == 'OUT_OF_SCOPE':
        status='DEFERRED'
        decision_reason='OUT_OF_SCOPE: requires explicit scope expansion before production'
    elif duplicate_status == 'DUPLICATE':
        status='DEFERRED'
        decision_reason=f'DUPLICATE: {overlap_reason}; explicit rework/reuse decision required'
    elif duplicate_status == 'NEEDS_REVIEW':
        status='TRIAGED'
        decision_reason=f'NEEDS_REVIEW: {overlap_reason}'
    else:
        status='READY_FOR_DECISION'
        decision_reason='Human SELECT/DEFER/REJECT/RESEARCH_MORE required before autonomous-radar promotion'
    if risk == 'TIER_3':
        decision_reason += '; TIER_3 requires human/science review if selected'

    notes = str(candidate.get('notes') or '').strip()
    if overlap_score:
        notes = (notes + ' | ' if notes else '') + f'semantic_overlap_score={overlap_score}'

    return RadarIdea(
        idea_id=idea_id,
        created_at=now.isoformat(),
        source_type=str(candidate.get('source_type') or 'UNKNOWN').strip().upper(),
        source_ref=str(candidate.get('source_ref') or '').strip(),
        title=str(candidate.get('title') or '').strip(),
        topic_domain=str(candidate.get('topic_domain') or '').strip().upper(),
        subtopic=str(candidate.get('subtopic') or '').strip(),
        persona=str(candidate.get('persona') or 'GENERAL').strip().upper(),
        problem=str(candidate.get('problem') or '').strip(),
        proposed_angle=str(candidate.get('proposed_angle') or '').strip(),
        why_now=str(candidate.get('why_now') or '').strip(),
        evidence_readiness=evidence,
        novelty_score=_clamp_score(candidate.get('novelty_score')),
        practical_value_score=_clamp_score(candidate.get('practical_value_score')),
        brand_fit_score=_clamp_score(candidate.get('brand_fit_score')),
        timeliness_score=_clamp_score(candidate.get('timeliness_score')),
        health_risk_tier=risk,
        duplicate_status=duplicate_status,
        status=status,
        human_decision='',
        promoted_master_id='',
        notes=notes,
        scope_class=scope,
        proposed_core_thesis=str(candidate.get('proposed_core_thesis') or candidate.get('core_thesis') or '').strip(),
        priority_score=priority,
        similar_master_ids=','.join(similar_ids),
        decision_reason=decision_reason,
    )


def rank_candidates(candidates: Sequence[Mapping[str, object]], *, existing_rows: Iterable[Mapping[str, object]] = (), existing_ids: Sequence[str] = (), now: datetime | None = None) -> list[RadarIdea]:
    now = now or datetime.now().astimezone()
    ids=list(existing_ids)
    out=[]
    existing=list(existing_rows)
    for candidate in candidates:
        idea_id=next_idea_id(ids, now)
        idea=triage_candidate(candidate, idea_id=idea_id, now=now, existing_rows=existing)
        ids.append(idea_id)
        out.append(idea)
        existing.append({
            'idea_id': idea.idea_id,
            'topic_domain': idea.topic_domain,
            'problem': idea.problem,
            'proposed_core_thesis': idea.proposed_core_thesis,
            'proposed_angle': idea.proposed_angle,
        })
    return sorted(out, key=lambda x: (-x.priority_score, x.idea_id))


def apply_human_decision(idea: RadarIdea, decision: str) -> RadarIdea:
    decision=str(decision or '').strip().upper()
    if decision not in VALID_DECISIONS:
        raise ValueError('invalid human decision')
    if decision == 'SELECT':
        if idea.scope_class == 'OUT_OF_SCOPE':
            raise ValueError('OUT_OF_SCOPE requires canonical scope expansion before SELECT')
        status='SELECTED'
    elif decision == 'DEFER':
        status='DEFERRED'
    elif decision == 'REJECT':
        status='REJECTED'
    else:
        status='TRIAGED'
    return replace(idea, human_decision=decision, status=status)


def promote_selected(idea: RadarIdea, master_id: str) -> RadarIdea:
    if idea.human_decision != 'SELECT' or idea.status != 'SELECTED':
        raise PermissionError('IDEA_SELECTION_REQUIRED')
    master_id=str(master_id or '').strip()
    if not master_id:
        raise ValueError('master_id required')
    return replace(idea, promoted_master_id=master_id, status='PROMOTED')
