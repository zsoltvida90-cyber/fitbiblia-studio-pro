from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Mapping, Sequence

QUEUE_COLUMNS = [
    'queue_id','created_at','updated_at','idea_id','master_id','asset_id','title','target_platform','output_type',
    'objective','persona','health_risk_tier','stage','owner','human_gate','priority','blocker_code','next_action',
    'due_at','job_id','qa_status','archive_id','publication_status','notes','scope_class',
]

STAGES = {
    'SELECTED','RESEARCHING','MASTER_DRAFT','MASTER_REVIEW','MASTER_APPROVED','PACKAGING','RENDERING','QA',
    'HUMAN_REVIEW','ACCEPTED','REVISION','REJECTED','ARCHIVED','SCHEDULED','PUBLISHED',
}

ALLOWED = {
    'SELECTED': {'RESEARCHING','MASTER_DRAFT','REJECTED'},
    'RESEARCHING': {'MASTER_DRAFT','REVISION','REJECTED'},
    'MASTER_DRAFT': {'MASTER_REVIEW','REVISION','REJECTED'},
    'MASTER_REVIEW': {'MASTER_APPROVED','REVISION','REJECTED'},
    'MASTER_APPROVED': {'PACKAGING','REJECTED'},
    'PACKAGING': {'RENDERING','QA','REVISION','REJECTED'},
    'RENDERING': {'QA','REVISION','REJECTED'},
    'QA': {'HUMAN_REVIEW','REVISION','REJECTED'},
    'HUMAN_REVIEW': {'ACCEPTED','REVISION','REJECTED'},
    'REVISION': {'MASTER_DRAFT','PACKAGING','RENDERING','QA','HUMAN_REVIEW','REJECTED'},
    'ACCEPTED': {'ARCHIVED'},
    'ARCHIVED': {'SCHEDULED','PUBLISHED'},
    'SCHEDULED': {'PUBLISHED'},
    'REJECTED': set(),
    'PUBLISHED': set(),
}

@dataclass(frozen=True)
class AuthorityState:
    master_approved: bool = False
    health_review_ok: bool = False
    human_acceptance: bool = False
    archive_verified: bool = False
    distribution_scheduled: bool = False
    distribution_published: bool = False

@dataclass(frozen=True)
class QueueItem:
    queue_id: str
    created_at: str
    updated_at: str
    idea_id: str
    master_id: str
    asset_id: str
    title: str
    target_platform: str
    output_type: str
    objective: str
    persona: str
    health_risk_tier: str
    stage: str
    owner: str
    human_gate: str
    priority: float
    blocker_code: str
    next_action: str
    due_at: str
    job_id: str
    qa_status: str
    archive_id: str
    publication_status: str
    notes: str
    scope_class: str

    def to_row(self) -> list[object]:
        return [getattr(self, c) for c in QUEUE_COLUMNS]


def next_queue_id(existing_ids: Sequence[str], now: datetime) -> str:
    prefix=f'QUEUE-{now:%Y%m%d}-'
    nums=[]
    for raw in existing_ids:
        m=re.fullmatch(re.escape(prefix)+r'(\d{3})', str(raw or ''))
        if m: nums.append(int(m.group(1)))
    return f'{prefix}{max(nums, default=0)+1:03d}'


def _score(v: object) -> float:
    try: return round(max(0.0,min(100.0,float(v or 0))),1)
    except (TypeError, ValueError): return 0.0


def create_from_selected_idea(idea: Mapping[str, object], *, queue_id: str, now: datetime, target_platform: str = '', output_type: str = '', objective: str = '', job_id: str = '') -> QueueItem:
    if str(idea.get('human_decision') or '').upper() != 'SELECT' or str(idea.get('status') or '').upper() not in {'SELECTED','PROMOTED'}:
        raise PermissionError('IDEA_SELECTION_REQUIRED')
    if str(idea.get('scope_class') or '').upper() == 'OUT_OF_SCOPE':
        raise PermissionError('SCOPE_EXPANSION_REQUIRED')
    return QueueItem(
        queue_id=queue_id,
        created_at=now.isoformat(), updated_at=now.isoformat(),
        idea_id=str(idea.get('idea_id') or ''), master_id=str(idea.get('promoted_master_id') or ''), asset_id='',
        title=str(idea.get('title') or ''), target_platform=str(target_platform or '').upper(), output_type=str(output_type or '').upper(),
        objective=str(objective or '').upper(), persona=str(idea.get('persona') or 'GENERAL').upper(),
        health_risk_tier=str(idea.get('health_risk_tier') or 'TIER_1').upper(), stage='SELECTED', owner='AI',
        human_gate='', priority=_score(idea.get('priority_score')), blocker_code='', next_action='resolve research/claim path and create brief',
        due_at='', job_id=job_id, qa_status='', archive_id='', publication_status='PLANNED',
        notes='Queue is a read/control model; authoritative master/archive/publication state must be verified separately.',
        scope_class=str(idea.get('scope_class') or '').upper(),
    )


def create_from_direct_request(*, queue_id: str, now: datetime, title: str, target_platform: str, output_type: str, objective: str, persona: str='GENERAL', health_risk_tier: str='TIER_1', scope_class: str='CORE', job_id: str='', selection_intent: bool=False) -> QueueItem:
    if not selection_intent:
        raise PermissionError('IDEA_SELECTION_REQUIRED')
    if scope_class.upper() == 'OUT_OF_SCOPE':
        raise PermissionError('SCOPE_EXPANSION_REQUIRED')
    return QueueItem(
        queue_id=queue_id, created_at=now.isoformat(), updated_at=now.isoformat(), idea_id='', master_id='', asset_id='',
        title=title, target_platform=target_platform.upper(), output_type=output_type.upper(), objective=objective.upper(), persona=persona.upper(),
        health_risk_tier=health_risk_tier.upper(), stage='SELECTED', owner='AI', human_gate='', priority=0.0, blocker_code='',
        next_action='run Ledger pre-check, scope/risk and research/claim path', due_at='', job_id=job_id, qa_status='', archive_id='',
        publication_status='PLANNED', notes='Direct explicit request supplied human selection intent. Queue remains non-authoritative.', scope_class=scope_class.upper(),
    )


def transition(item: QueueItem, target_stage: str, *, now: datetime, authority: AuthorityState = AuthorityState(), master_id: str='', asset_id: str='', archive_id: str='', qa_status: str='', blocker_code: str='', next_action: str='', human_gate: str='', notes: str='') -> QueueItem:
    target=target_stage.upper()
    if target not in STAGES:
        raise ValueError('QUEUE_STAGE_INVALID')
    if target not in ALLOWED.get(item.stage, set()):
        raise PermissionError('QUEUE_TRANSITION_INVALID')

    resolved_master=master_id or item.master_id
    resolved_asset=asset_id or item.asset_id
    resolved_archive=archive_id or item.archive_id
    resolved_qa=(qa_status or item.qa_status).upper()
    publication=item.publication_status

    if target == 'MASTER_APPROVED':
        if not authority.master_approved or not resolved_master:
            raise PermissionError('MASTER_AUTHORITY_REQUIRED')
        if item.health_risk_tier == 'TIER_3' and not authority.health_review_ok:
            raise PermissionError('HEALTH_RISK_REVIEW_REQUIRED')
    if target == 'ACCEPTED':
        if not authority.human_acceptance:
            raise PermissionError('HUMAN_ACCEPTANCE_REQUIRED')
        if resolved_qa not in {'PASS','HUMAN_APPROVED'}:
            raise PermissionError('QA_PASS_REQUIRED')
    if target == 'ARCHIVED':
        if not authority.archive_verified or not resolved_archive:
            raise PermissionError('ARCHIVE_LEDGER_VERIFY_FAIL')
    if target == 'SCHEDULED':
        if not authority.distribution_scheduled:
            raise PermissionError('DISTRIBUTION_AUTHORITY_REQUIRED')
        publication='SCHEDULED'
    if target == 'PUBLISHED':
        if not authority.distribution_published:
            raise PermissionError('DISTRIBUTION_AUTHORITY_REQUIRED')
        publication='PUBLISHED'

    default_owner='AI'
    default_gate=''
    default_next=''
    if target in {'MASTER_REVIEW','HUMAN_REVIEW'}:
        default_owner='HUMAN'; default_gate=target
    elif target == 'ACCEPTED':
        default_owner='SYSTEM'; default_next='run immutable Product Archive flow'
    elif target == 'ARCHIVED':
        default_owner='AI'; default_next='publish/schedule only if separately authorized'
    elif target in {'SCHEDULED','PUBLISHED'}:
        default_owner='SYSTEM'

    return replace(
        item, updated_at=now.isoformat(), stage=target, owner=default_owner,
        human_gate=human_gate or default_gate, blocker_code=blocker_code,
        next_action=next_action or default_next, master_id=resolved_master, asset_id=resolved_asset,
        archive_id=resolved_archive, qa_status=resolved_qa, publication_status=publication,
        notes=(item.notes + (' | ' if item.notes and notes else '') + notes),
    )
