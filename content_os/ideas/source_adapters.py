from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Mapping, Any

VALID_EVIDENCE = {'KNOWN_APPROVED','REUSABLE_RESEARCH','RESEARCH_NEEDED','CONTESTED','UNSUPPORTED','UNKNOWN'}

@dataclass(frozen=True)
class CandidatePacket:
    source_type: str
    source_ref: str
    title: str
    topic_domain: str
    subtopic: str
    persona: str
    problem: str
    proposed_angle: str
    proposed_core_thesis: str
    why_now: str
    evidence_readiness: str
    novelty_score: float
    practical_value_score: float
    brand_fit_score: float
    timeliness_score: float
    health_risk_tier: str = ''
    scope_class: str = ''
    notes: str = ''

    def as_mapping(self) -> dict[str, Any]:
        return asdict(self)


def _score(value: object, default: float = 50.0) -> float:
    try:
        if value in (None, ''):
            return default
        return round(max(0.0, min(100.0, float(value))), 1)
    except (TypeError, ValueError):
        return default


def _editorial_fields(editorial: Mapping[str, object]) -> dict[str, object]:
    required = ('title','topic_domain','problem','proposed_angle','proposed_core_thesis')
    missing = [k for k in required if not str(editorial.get(k) or '').strip()]
    if missing:
        raise ValueError('CANDIDATE_SYNTHESIS_REQUIRED:' + ','.join(missing))
    evidence = str(editorial.get('evidence_readiness') or 'UNKNOWN').strip().upper()
    if evidence not in VALID_EVIDENCE:
        evidence = 'UNKNOWN'
    return {
        'title': str(editorial.get('title')).strip(),
        'topic_domain': str(editorial.get('topic_domain')).strip().upper(),
        'subtopic': str(editorial.get('subtopic') or '').strip(),
        'persona': str(editorial.get('persona') or 'GENERAL').strip().upper(),
        'problem': str(editorial.get('problem')).strip(),
        'proposed_angle': str(editorial.get('proposed_angle')).strip(),
        'proposed_core_thesis': str(editorial.get('proposed_core_thesis')).strip(),
        'why_now': str(editorial.get('why_now') or '').strip(),
        'evidence_readiness': evidence,
        'novelty_score': _score(editorial.get('novelty_score')),
        'practical_value_score': _score(editorial.get('practical_value_score')),
        'brand_fit_score': _score(editorial.get('brand_fit_score')),
        'timeliness_score': _score(editorial.get('timeliness_score')),
        'health_risk_tier': str(editorial.get('health_risk_tier') or '').strip().upper(),
        'scope_class': str(editorial.get('scope_class') or '').strip().upper(),
    }


def manual_packet(editorial: Mapping[str, object], *, source_ref: str = 'human://direct-request') -> CandidatePacket:
    fields = _editorial_fields(editorial)
    return CandidatePacket(source_type='MANUAL', source_ref=source_ref, notes='Direct/manual candidate; explicit user request may already carry selection intent.', **fields)


def research_finding_packet(row: Mapping[str, object], editorial: Mapping[str, object]) -> CandidatePacket:
    finding_id = str(row.get('finding_id') or '').strip()
    research_id = str(row.get('research_id') or '').strip()
    finding = str(row.get('finding') or '').strip()
    if not finding_id or not research_id or not finding:
        raise ValueError('RESEARCH_FINDING_INCOMPLETE')
    fields = _editorial_fields(editorial)
    integrity = str(row.get('integrity_gate') or '').strip().upper()
    freshness = str(row.get('freshness_gate') or '').strip().upper()
    reusable = str(row.get('reusable') or '').strip().upper()
    if fields['evidence_readiness'] == 'UNKNOWN':
        fields['evidence_readiness'] = 'REUSABLE_RESEARCH' if integrity == 'OK' and freshness == 'FRESH' and reusable == 'YES' else 'RESEARCH_NEEDED'
    if fields['evidence_readiness'] == 'KNOWN_APPROVED':
        raise ValueError('RESEARCH_LIBRARY_NOT_CLAIM_AUTHORITY')
    adopted = str(row.get('adopted_in_refs') or '').strip()
    note_parts = [
        f"finding_type={str(row.get('finding_type') or '').strip()}",
        f"confidence={str(row.get('confidence') or '').strip()}",
        f"implementation_status={str(row.get('implementation_status') or '').strip()}",
        'Research Library finding is navigation/context, not automatic scientific claim authority.',
    ]
    if adopted:
        note_parts.append(f'adopted_in_refs={adopted}')
    return CandidatePacket(
        source_type='RESEARCH_LIBRARY',
        source_ref=f'research://{research_id}/finding/{finding_id}',
        notes=' | '.join(note_parts),
        **fields,
    )


def audience_signal_packet(row: Mapping[str, object], editorial: Mapping[str, object]) -> CandidatePacket:
    signal_id = str(row.get('signal_id') or '').strip()
    if not signal_id:
        raise ValueError('AUDIENCE_SIGNAL_INCOMPLETE')
    fields = _editorial_fields(editorial)
    if fields['evidence_readiness'] == 'KNOWN_APPROVED':
        raise ValueError('AUDIENCE_SIGNAL_NOT_CLAIM_AUTHORITY')
    recurrence = str(row.get('recurrence_state') or '').strip().upper() or 'UNKNOWN'
    confidence = str(row.get('confidence') or '').strip().upper() or 'UNKNOWN'
    return CandidatePacket(
        source_type='AUDIENCE_SIGNAL',
        source_ref=f'audience-signal://{signal_id}',
        notes=f'recurrence_state={recurrence} | signal_confidence={confidence} | Audience signal indicates demand/language, not scientific truth.',
        **fields,
    )


def current_research_packet(source_ref: str, editorial: Mapping[str, object]) -> CandidatePacket:
    if not str(source_ref or '').strip():
        raise ValueError('SOURCE_REF_REQUIRED')
    fields = _editorial_fields(editorial)
    if fields['evidence_readiness'] in {'UNKNOWN','REUSABLE_RESEARCH','KNOWN_APPROVED'}:
        fields['evidence_readiness'] = 'RESEARCH_NEEDED'
    return CandidatePacket(
        source_type='CURRENT_RESEARCH',
        source_ref=str(source_ref).strip(),
        notes='Fresh external/current source candidate. Science validation and Research Library save are still required before material publishable claims.',
        **fields,
    )


def editorial_gap_packet(gap_ref: str, editorial: Mapping[str, object]) -> CandidatePacket:
    if not str(gap_ref or '').strip():
        raise ValueError('GAP_REF_REQUIRED')
    fields = _editorial_fields(editorial)
    if fields['evidence_readiness'] == 'KNOWN_APPROVED' and not str(editorial.get('approved_claim_ids') or '').strip():
        fields['evidence_readiness'] = 'UNKNOWN'
    return CandidatePacket(
        source_type='EDITORIAL_GAP',
        source_ref=str(gap_ref).strip(),
        notes='Editorial gap is a planning signal, not evidence.',
        **fields,
    )
