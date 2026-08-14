from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping, Sequence

FEEDBACK_COLUMNS = [
    'feedback_id','created_at','job_id','master_id','asset_id','feedback_type','stage','ai_version_ref','human_version_ref',
    'field_or_component','before_summary','after_summary','reason','outcome','confidence','reusable_scope','candidate_rule',
    'rule_status','linked_experiment_id','accepted_archive_id','notes',
]
VALID_TYPES={'HOOK','COPY','SCIENCE_WORDING','STRUCTURE','VISUAL','CTA','TONE','FORMAT','PROCESS'}
VALID_RULE_STATUS={'OBSERVATION','HYPOTHESIS','ADOPTED','REJECTED'}
VALID_CONFIDENCE={'LOW','MEDIUM','HIGH'}

@dataclass(frozen=True)
class FeedbackRecord:
    feedback_id: str
    created_at: str
    job_id: str
    master_id: str
    asset_id: str
    feedback_type: str
    stage: str
    ai_version_ref: str
    human_version_ref: str
    field_or_component: str
    before_summary: str
    after_summary: str
    reason: str
    outcome: str
    confidence: str
    reusable_scope: str
    candidate_rule: str
    rule_status: str
    linked_experiment_id: str
    accepted_archive_id: str
    notes: str

    def to_row(self) -> list[object]:
        return [getattr(self,c) for c in FEEDBACK_COLUMNS]

@dataclass(frozen=True)
class FeedbackPattern:
    pattern_key: str
    feedback_type: str
    reusable_scope: str
    candidate_rule: str
    accepted_records: int
    unique_assets: int
    unique_archives: int
    status: str
    confidence: str
    requires_science_review: bool
    reason: str


def _norm(text: str) -> str:
    text=unicodedata.normalize('NFKD', str(text or ''))
    text=''.join(c for c in text if not unicodedata.combining(c)).lower()
    return ' '.join(re.findall(r'[a-z0-9]+',text))


def next_feedback_id(existing_ids: Sequence[str], now: datetime) -> str:
    prefix=f'FB-{now:%Y%m%d}-'; nums=[]
    for raw in existing_ids:
        m=re.fullmatch(re.escape(prefix)+r'(\d{3})',str(raw or ''))
        if m: nums.append(int(m.group(1)))
    return f'{prefix}{max(nums,default=0)+1:03d}'


def create_feedback(*, feedback_id: str, now: datetime, feedback_type: str, field_or_component: str, before_summary: str, after_summary: str, reason: str, outcome: str, confidence: str='MEDIUM', reusable_scope: str='', candidate_rule: str='', job_id: str='', master_id: str='', asset_id: str='', stage: str='', ai_version_ref: str='', human_version_ref: str='', linked_experiment_id: str='', accepted_archive_id: str='', notes: str='') -> FeedbackRecord:
    ftype=feedback_type.upper().strip()
    if ftype not in VALID_TYPES: raise ValueError('FEEDBACK_TYPE_INVALID')
    conf=confidence.upper().strip()
    if conf not in VALID_CONFIDENCE: raise ValueError('FEEDBACK_CONFIDENCE_INVALID')
    if not reason.strip(): raise ValueError('FEEDBACK_REASON_REQUIRED')
    if _norm(before_summary)==_norm(after_summary): raise ValueError('FEEDBACK_DELTA_REQUIRED')
    return FeedbackRecord(
        feedback_id=feedback_id,created_at=now.isoformat(),job_id=job_id,master_id=master_id,asset_id=asset_id,
        feedback_type=ftype,stage=stage,ai_version_ref=ai_version_ref,human_version_ref=human_version_ref,
        field_or_component=field_or_component,before_summary=before_summary,after_summary=after_summary,reason=reason,
        outcome=outcome.upper().strip(),confidence=conf,reusable_scope=reusable_scope.upper().strip(),candidate_rule=candidate_rule.strip(),
        rule_status='OBSERVATION',linked_experiment_id=linked_experiment_id,accepted_archive_id=accepted_archive_id,notes=notes,
    )


def pattern_key(record: Mapping[str, object]) -> str:
    return '|'.join([
        str(record.get('feedback_type') or '').upper().strip(),
        str(record.get('reusable_scope') or '').upper().strip(),
        _norm(str(record.get('candidate_rule') or '')),
    ])


def synthesize_patterns(records: Iterable[Mapping[str, object]], *, min_records: int=3, min_unique_assets: int=2) -> list[FeedbackPattern]:
    groups: dict[str,list[Mapping[str,object]]]={}
    for r in records:
        if str(r.get('rule_status') or 'OBSERVATION').upper() == 'REJECTED': continue
        if not str(r.get('candidate_rule') or '').strip(): continue
        if str(r.get('outcome') or '').upper() not in {'ACCEPTED','ACCEPTED_WITH_IMPROVEMENT_BACKLOG','HUMAN_APPROVED'}: continue
        groups.setdefault(pattern_key(r),[]).append(r)
    out=[]
    for key,grp in groups.items():
        assets={str(r.get('asset_id') or '').strip() for r in grp if str(r.get('asset_id') or '').strip()}
        archives={str(r.get('accepted_archive_id') or '').strip() for r in grp if str(r.get('accepted_archive_id') or '').strip()}
        enough=len(grp)>=min_records and len(assets)>=min_unique_assets
        status='HYPOTHESIS' if enough else 'OBSERVATION'
        confidence='MEDIUM' if enough else 'LOW'
        if enough and len(archives)>=2: confidence='HIGH'
        first=grp[0]
        ftype=str(first.get('feedback_type') or '').upper()
        out.append(FeedbackPattern(
            pattern_key=key,feedback_type=ftype,reusable_scope=str(first.get('reusable_scope') or '').upper(),
            candidate_rule=str(first.get('candidate_rule') or ''),accepted_records=len(grp),unique_assets=len(assets),unique_archives=len(archives),
            status=status,confidence=confidence,requires_science_review=(ftype=='SCIENCE_WORDING'),
            reason=('repeated accepted pattern; eligible for human review as a hypothesis' if enough else 'insufficient independent accepted repetitions'),
        ))
    return sorted(out,key=lambda p:(p.status!='HYPOTHESIS',-p.accepted_records,p.pattern_key))


def adopt_pattern(pattern: FeedbackPattern, *, human_approved: bool=False, canonical_policy_ref: str='') -> dict[str, object]:
    if not human_approved: raise PermissionError('HUMAN_POLICY_APPROVAL_REQUIRED')
    if pattern.status != 'HYPOTHESIS': raise PermissionError('FEEDBACK_HYPOTHESIS_REQUIRED')
    if pattern.requires_science_review: raise PermissionError('SCIENCE_POLICY_REVIEW_REQUIRED')
    if not canonical_policy_ref.strip(): raise ValueError('CANONICAL_POLICY_REF_REQUIRED')
    return {'pattern_key':pattern.pattern_key,'rule_status':'ADOPTED','canonical_policy_ref':canonical_policy_ref,'note':'Adoption records approval intent; active policy must actually be updated and verified separately.'}
