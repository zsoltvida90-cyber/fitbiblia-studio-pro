from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping

VALID_SOURCE_TYPES = {
    'YOUTUBE_TRANSCRIPT',
    'PODCAST_TRANSCRIPT',
    'INTERVIEW_TRANSCRIPT',
    'LECTURE_TRANSCRIPT',
    'WEBINAR_TRANSCRIPT',
    'USER_PROVIDED_TRANSCRIPT',
    'AUTHOR_MANUSCRIPT',
    'PREPRINT',
    'AUTHOR_BOOK',
    'BOOK_NOTES',
    'AUTHOR_ARTICLE',
    'NEWSLETTER',
    'PERSONAL_RESEARCH_REPORT',
    'DATASET',
    'METHOD_NOTE',
    'WEBSITE_ARTICLE',
    'OTHER_EXTERNAL',
}

VALID_KNOWLEDGE_LANES = {
    'SCIENCE_EVIDENCE',
    'EXPERT_CONTEXT',
    'CASE_EXPERIENCE',
    'OPEN_QUESTION',
    'AUDIENCE_SIGNAL',
}

VALID_SOURCE_ROLES = {
    'CONTEXT',
    'HYPOTHESIS',
    'QUESTION',
    'CASE',
    'PRIMARY_CANDIDATE',
}

VALID_REVIEW_STATES = {
    'PEER_REVIEWED',
    'PREPRINT',
    'UNPUBLISHED',
    'AUTHOR_REPORTED',
    'NOT_APPLICABLE',
    'UNKNOWN',
}

TRANSCRIPT_TYPES = {
    'YOUTUBE_TRANSCRIPT',
    'PODCAST_TRANSCRIPT',
    'INTERVIEW_TRANSCRIPT',
    'LECTURE_TRANSCRIPT',
    'WEBINAR_TRANSCRIPT',
    'USER_PROVIDED_TRANSCRIPT',
}

SCIENCE_CANDIDATE_TYPES = {
    'AUTHOR_MANUSCRIPT',
    'PREPRINT',
    'PERSONAL_RESEARCH_REPORT',
    'DATASET',
    'METHOD_NOTE',
}


@dataclass(frozen=True)
class ExternalSourcePacket:
    source_type: str
    source_ref: str
    title: str
    creator: str
    publication_date: str = ''
    language: str = ''
    transcript_ref: str = ''
    transcript_origin: str = ''
    transcript_locator: str = ''
    primary_artifact_refs: str = ''
    source_role: str = 'CONTEXT'
    knowledge_lane: str = 'EXPERT_CONTEXT'
    review_state: str = 'UNKNOWN'
    attribution_required: bool = True
    factual_claim_upgrade_allowed: bool = False
    notes: str = ''

    def as_mapping(self) -> dict[str, Any]:
        return asdict(self)


def _clean(value: object) -> str:
    return str(value or '').strip()


def _default_lane(source_type: str) -> str:
    if source_type in SCIENCE_CANDIDATE_TYPES:
        return 'SCIENCE_EVIDENCE'
    return 'EXPERT_CONTEXT'


def normalize_external_source(source: Mapping[str, object]) -> ExternalSourcePacket:
    source_type = _clean(source.get('source_type')).upper() or 'OTHER_EXTERNAL'
    if source_type not in VALID_SOURCE_TYPES:
        source_type = 'OTHER_EXTERNAL'

    source_ref = _clean(source.get('source_ref'))
    title = _clean(source.get('title'))
    creator = _clean(source.get('creator') or source.get('author') or source.get('speaker'))
    if not source_ref:
        raise ValueError('EXTERNAL_SOURCE_REF_REQUIRED')
    if not title:
        raise ValueError('EXTERNAL_SOURCE_TITLE_REQUIRED')
    if not creator:
        raise ValueError('EXTERNAL_SOURCE_CREATOR_REQUIRED')

    lane = _clean(source.get('knowledge_lane')).upper() or _default_lane(source_type)
    if lane not in VALID_KNOWLEDGE_LANES:
        raise ValueError('EXTERNAL_SOURCE_KNOWLEDGE_LANE_INVALID')
    if lane == 'AUDIENCE_SIGNAL':
        raise ValueError('EXTERNAL_SOURCE_NOT_AUDIENCE_SIGNAL')

    role = _clean(source.get('source_role')).upper() or (
        'PRIMARY_CANDIDATE' if source_type in SCIENCE_CANDIDATE_TYPES else 'CONTEXT'
    )
    if role not in VALID_SOURCE_ROLES:
        raise ValueError('EXTERNAL_SOURCE_ROLE_INVALID')

    review_state = _clean(source.get('review_state')).upper() or 'UNKNOWN'
    if review_state not in VALID_REVIEW_STATES:
        review_state = 'UNKNOWN'

    primary_artifact_refs = _clean(source.get('primary_artifact_refs'))
    note_parts = []
    raw_notes = _clean(source.get('notes'))
    if raw_notes:
        note_parts.append(raw_notes)
    if source_type in TRANSCRIPT_TYPES:
        note_parts.append(
            'Transcript/expert material is contextual authority unless an eligible primary artifact is independently validated.'
        )
    if review_state in {'PREPRINT', 'UNPUBLISHED', 'AUTHOR_REPORTED'}:
        note_parts.append(
            'Non-peer-reviewed status must remain visible; do not describe as established consensus.'
        )
    if primary_artifact_refs:
        note_parts.append(
            'Follow linked primary artifacts separately; source-chain identity must be preserved.'
        )
    elif source_type in TRANSCRIPT_TYPES:
        note_parts.append(
            'If the speaker cites own research/manuscript/book/data, attempt to resolve that artifact before upgrading any factual claim.'
        )

    return ExternalSourcePacket(
        source_type=source_type,
        source_ref=source_ref,
        title=title,
        creator=creator,
        publication_date=_clean(source.get('publication_date')),
        language=_clean(source.get('language')),
        transcript_ref=_clean(source.get('transcript_ref')),
        transcript_origin=_clean(source.get('transcript_origin')),
        transcript_locator=_clean(source.get('transcript_locator')),
        primary_artifact_refs=primary_artifact_refs,
        source_role=role,
        knowledge_lane=lane,
        review_state=review_state,
        attribution_required=True,
        factual_claim_upgrade_allowed=False,
        notes=' | '.join(note_parts),
    )
