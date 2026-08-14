from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping, Sequence

CONTROL_CENTER_COLUMNS = [
    'snapshot_at','rank','section','item_ref','title','state','priority','blocker_code','next_action',
    'human_action_required','source_table','authority_note','notes',
]

HUMAN_BLOCKERS = {
    'IDEA_SELECTION_REQUIRED','DUPLICATE_REUSE_APPROVAL_REQUIRED','SCOPE_EXPANSION_REQUIRED',
    'HEALTH_RISK_REVIEW_REQUIRED','HUMAN_ACCEPTANCE_REQUIRED','HUMAN_POLICY_APPROVAL_REQUIRED',
    'HUMAN_VISUAL_APPROVAL_REQUIRED','HUMAN_GOLDEN_NOMINATION_REQUIRED','HUMAN_GOLDEN_APPROVAL_REQUIRED',
    'SCIENCE_POLICY_REVIEW_REQUIRED','HUMAN_REVIEW',
}

@dataclass(frozen=True)
class ControlCard:
    snapshot_at: str
    rank: int
    section: str
    item_ref: str
    title: str
    state: str
    priority: float
    blocker_code: str
    next_action: str
    human_action_required: str
    source_table: str
    authority_note: str
    notes: str = ''

    def to_row(self) -> list[object]:
        return [getattr(self, c) for c in CONTROL_CENTER_COLUMNS]


def _score(value: object) -> float:
    try:
        return round(max(0.0, min(100.0, float(value or 0))), 1)
    except (TypeError, ValueError):
        return 0.0


def _yes(value: bool) -> str:
    return 'YES' if value else 'NO'


def _card(now: datetime, *, rank: int, section: str, item_ref: str, title: str, state: str,
          priority: object = 0, blocker_code: str = '', next_action: str = '', human: bool = False,
          source_table: str, authority_note: str, notes: str = '') -> ControlCard:
    return ControlCard(now.isoformat(), rank, section, item_ref, title, state, _score(priority), blocker_code,
                       next_action, _yes(human), source_table, authority_note, notes)


def build_cards(*, now: datetime,
                idea_rows: Iterable[Mapping[str, object]] = (),
                queue_rows: Iterable[Mapping[str, object]] = (),
                feedback_rows: Iterable[Mapping[str, object]] = (),
                experiment_rows: Iterable[Mapping[str, object]] = (),
                golden_rows: Iterable[Mapping[str, object]] = (),
                run_rows: Iterable[Mapping[str, object]] = (),
                audience_rows: Iterable[Mapping[str, object]] = ()) -> list[ControlCard]:
    cards: list[ControlCard] = []

    for r in idea_rows:
        status = str(r.get('status') or '').upper()
        ref = str(r.get('idea_id') or '').strip()
        if not ref:
            continue
        title = str(r.get('title') or ref)
        dup = str(r.get('duplicate_status') or '').upper()
        if status == 'READY_FOR_DECISION':
            cards.append(_card(now, rank=10, section='DECIDE_IDEA', item_ref=ref, title=title, state=status,
                               priority=r.get('priority_score'), next_action='SELECT / DEFER / REJECT / RESEARCH_MORE',
                               human=True, source_table='IDEA_INBOX', authority_note='Idea decision only; does not approve master/publication.',
                               notes=str(r.get('decision_reason') or '')))
        elif status == 'TRIAGED' and not str(r.get('human_decision') or '').strip():
            cards.append(_card(now, rank=35, section='TRIAGE_REVIEW', item_ref=ref, title=title, state=status,
                               priority=r.get('priority_score'), blocker_code='SEMANTIC_OR_EVIDENCE_REVIEW',
                               next_action='resolve missing thesis/dedup/evidence readiness', human=False,
                               source_table='IDEA_INBOX', authority_note='AI may resolve mechanical/research gaps; human SELECT still required later.'))
        elif dup == 'DUPLICATE' and status == 'DEFERRED':
            cards.append(_card(now, rank=55, section='DEFERRED_DUPLICATE', item_ref=ref, title=title, state=status,
                               priority=r.get('priority_score'), blocker_code='DUPLICATE_REUSE_APPROVAL_REQUIRED',
                               next_action='ignore, rework angle, or explicitly approve reuse', human=True,
                               source_table='IDEA_INBOX', authority_note='Reuse still requires Ledger collision/distribution gate.'))

    for r in queue_rows:
        ref = str(r.get('queue_id') or '').strip()
        if not ref:
            continue
        stage = str(r.get('stage') or '').upper()
        blocker = str(r.get('blocker_code') or '').upper()
        title = str(r.get('title') or ref)
        human = str(r.get('human_gate') or '').strip() != '' or blocker in HUMAN_BLOCKERS or stage in {'MASTER_REVIEW','HUMAN_REVIEW'}
        if blocker:
            cards.append(_card(now, rank=5 if human else 25, section='BLOCKED', item_ref=ref, title=title, state=stage,
                               priority=r.get('priority'), blocker_code=blocker,
                               next_action=str(r.get('next_action') or 'resolve blocker'), human=human,
                               source_table='PRODUCTION_QUEUE', authority_note='Queue blocker is operational; verify the referenced authority before clearing.'))
        elif stage == 'HUMAN_REVIEW':
            cards.append(_card(now, rank=8, section='REVIEW_PRODUCT', item_ref=ref, title=title, state=stage,
                               priority=r.get('priority'), next_action='review delivered candidate: ACCEPT / REVISION / REJECT',
                               human=True, source_table='PRODUCTION_QUEUE', authority_note='Human review does not imply acceptance/archive/publication.'))
        elif stage == 'MASTER_REVIEW':
            cards.append(_card(now, rank=12, section='REVIEW_MASTER', item_ref=ref, title=title, state=stage,
                               priority=r.get('priority'), next_action='review semantic master and evidence/caveats', human=True,
                               source_table='PRODUCTION_QUEUE', authority_note='APPROVED_MASTER requires authoritative master record/integrity gate.'))
        elif stage == 'REVISION':
            cards.append(_card(now, rank=22, section='REVISION', item_ref=ref, title=title, state=stage,
                               priority=r.get('priority'), next_action=str(r.get('next_action') or 'revise and re-run affected gates'),
                               human=False, source_table='PRODUCTION_QUEUE', authority_note='Revision returns through affected authoritative gates.'))
        elif stage in {'SELECTED','RESEARCHING','MASTER_DRAFT','MASTER_APPROVED','PACKAGING','RENDERING','QA'}:
            cards.append(_card(now, rank=60, section='AI_WORKING', item_ref=ref, title=title, state=stage,
                               priority=r.get('priority'), next_action=str(r.get('next_action') or ''), human=False,
                               source_table='PRODUCTION_QUEUE', authority_note='Progress view only; queue stage is not authoritative truth.'))
        elif stage == 'ARCHIVED' and str(r.get('publication_status') or '').upper() == 'PLANNED':
            cards.append(_card(now, rank=40, section='READY_FOR_PUBLICATION_DECISION', item_ref=ref, title=title, state=stage,
                               priority=r.get('priority'), next_action='publish/schedule only when separately authorized', human=True,
                               source_table='PRODUCTION_QUEUE', authority_note='Verify DISTRIBUTION_LOG before schedule/publish; archive is not publication.'))

    for r in feedback_rows:
        if str(r.get('rule_status') or '').upper() != 'HYPOTHESIS':
            continue
        ref = str(r.get('feedback_id') or '').strip() or str(r.get('candidate_rule') or '')[:80]
        ftype = str(r.get('feedback_type') or '').upper()
        cards.append(_card(now, rank=18, section='REVIEW_FEEDBACK_HYPOTHESIS', item_ref=ref,
                           title=str(r.get('candidate_rule') or 'Editorial feedback hypothesis'), state='HYPOTHESIS',
                           next_action='review hypothesis; adopt/reject only through explicit policy process', human=True,
                           blocker_code='SCIENCE_POLICY_REVIEW_REQUIRED' if ftype == 'SCIENCE_WORDING' else 'HUMAN_POLICY_APPROVAL_REQUIRED',
                           source_table='EDITORIAL_FEEDBACK', authority_note='Feedback hypothesis is observation memory, not policy.'))

    for r in golden_rows:
        if str(r.get('status') or '').upper() != 'CANDIDATE':
            continue
        ref = str(r.get('golden_id') or '').strip()
        cards.append(_card(now, rank=16, section='REVIEW_GOLDEN', item_ref=ref, title=str(r.get('quality_reason') or ref),
                           state='CANDIDATE', next_action='visually compare baseline and approve/reject Golden status', human=True,
                           blocker_code='HUMAN_GOLDEN_APPROVAL_REQUIRED', source_table='GOLDEN_SET',
                           authority_note='Golden activation also requires verified accepted archive.'))

    for r in experiment_rows:
        status = str(r.get('status') or '').upper()
        ref = str(r.get('experiment_id') or '').strip()
        if not ref:
            continue
        if status == 'COMPLETE' and not str(r.get('learning_id') or '').strip():
            cards.append(_card(now, rank=30, section='EXPERIMENT_LEARNING', item_ref=ref,
                               title=str(r.get('hypothesis') or ref), state=status,
                               next_action='review descriptive result and decide whether to create a learning hypothesis', human=False,
                               source_table='EXPERIMENT_LOG', authority_note='Experiment result is descriptive; cannot mutate science/policy automatically.'))
        elif status == 'PLANNED':
            cards.append(_card(now, rank=65, section='EXPERIMENT_PLANNED', item_ref=ref,
                               title=str(r.get('hypothesis') or ref), state=status,
                               next_action='start only after both variants have valid distribution authority', human=False,
                               source_table='EXPERIMENT_LOG', authority_note='Planned experiment is not evidence.'))

    for r in run_rows:
        status = str(r.get('status') or '').upper()
        if status not in {'FAIL','BLOCKED','NEEDS_HUMAN'}:
            continue
        ref = str(r.get('run_id') or '').strip()
        blocker = str(r.get('error_code') or '').upper()
        human = status == 'NEEDS_HUMAN' or blocker in HUMAN_BLOCKERS or str(r.get('human_action_required') or '').upper() == 'YES'
        cards.append(_card(now, rank=1 if human else 3, section='SYSTEM_ISSUE', item_ref=ref,
                           title=str(r.get('operation') or ref), state=status, blocker_code=blocker,
                           next_action='inspect failure and retry mechanical work only after root cause is known', human=human,
                           source_table='SYSTEM_RUN_LOG', authority_note='Run log is observability, not editorial/scientific truth.',
                           notes=str(r.get('notes') or '')))

    seen_audience: set[str] = set()
    for r in audience_rows:
        state = str(r.get('recurrence_state') or '').upper()
        key = str(r.get('cluster_key') or '').strip()
        if state not in {'RECURRING','VALIDATED_PATTERN'} or not key or key in seen_audience:
            continue
        seen_audience.add(key)
        linked = str(r.get('linked_idea_id') or '').strip()
        if linked:
            continue
        cards.append(_card(now, rank=45, section='AUDIENCE_OPPORTUNITY', item_ref=key,
                           title=str(r.get('normalized_problem') or 'Recurring audience signal'), state=state,
                           next_action='synthesize one candidate packet and pass through Idea Radar', human=False,
                           source_table='AUDIENCE_SIGNAL', authority_note='Audience recurrence signals demand only; evidence_readiness starts UNKNOWN.'))

    cards.sort(key=lambda c: (c.rank, -c.priority, c.section, c.item_ref))
    return cards


def summarize(cards: Sequence[ControlCard]) -> dict[str, object]:
    sections: dict[str, int] = {}
    human = 0
    for c in cards:
        sections[c.section] = sections.get(c.section, 0) + 1
        if c.human_action_required == 'YES':
            human += 1
    return {
        'card_count': len(cards),
        'human_action_count': human,
        'sections': sections,
        'authority': 'READ_MODEL_ONLY',
        'warning': 'Never use Control Center labels/counts to override CONTENT_MASTER, DISTRIBUTION_LOG, PRODUCT_ARCHIVE, Knowledge Registry or Research Index authority.',
    }


def rows_for_sheet(cards: Sequence[ControlCard]) -> list[list[object]]:
    return [CONTROL_CENTER_COLUMNS] + [c.to_row() for c in cards]
