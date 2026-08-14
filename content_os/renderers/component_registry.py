from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

VALID_STATUS={'EXPERIMENTAL','ACTIVE','RETIRED'}
VALID_ROLES={'COVER','INNER_EXPLAIN','MECHANISM','MYTH','LIST_PROTOCOL','INSIGHT_WHISPER','EVIDENCE','CTA'}

@dataclass(frozen=True)
class ComponentSpec:
    component_id: str
    status: str
    roles: tuple[str,...]
    max_headline_chars: int
    max_body_chars: int
    max_hook_chars: int
    alignment: str
    foil_policy: str
    safe_zone: tuple[int,int,int,int]
    notes: str=''

COMPONENTS: dict[str,ComponentSpec]={
    'COVER_BIG_HOOK': ComponentSpec('COVER_BIG_HOOK','EXPERIMENTAL',('COVER',),70,95,55,'CENTER','ONE_FOCAL_HOOK',(110,150,970,1120),'Large stop-scroll cover with restrained body.'),
    'COVER_STAT': ComponentSpec('COVER_STAT','EXPERIMENTAL',('COVER',),65,105,35,'CENTER','STAT_OR_HOOK_ONLY',(110,150,970,1120),'Evidence/stat-led cover; stat wording must remain claim-safe.'),
    'INNER_EXPLAIN': ComponentSpec('INNER_EXPLAIN','EXPERIMENTAL',('INNER_EXPLAIN',),95,300,45,'CENTER','OPTIONAL_SMALL',(120,210,960,1120),'Calm explanatory inner slide.'),
    'NUMBER_EVIDENCE': ComponentSpec('NUMBER_EVIDENCE','EXPERIMENTAL',('EVIDENCE',),90,280,26,'CENTER','NUMBER_FOCAL_ONLY',(120,190,960,1120),'One quantitative result with caveat/source space.'),
    'MYTH_SPLIT': ComponentSpec('MYTH_SPLIT','EXPERIMENTAL',('MYTH',),85,240,35,'CENTER','CORRECTION_ONLY',(120,190,960,1120),'Myth/correction contrast without generic infographic cards.'),
    'MECHANISM_FLOW': ComponentSpec('MECHANISM_FLOW','EXPERIMENTAL',('MECHANISM',),85,260,30,'CENTER','OPTIONAL_SMALL',(120,180,960,1120),'Simple causal sequence; no decorative diagram overload.'),
    'THREE_STEP_PROTOCOL': ComponentSpec('THREE_STEP_PROTOCOL','EXPERIMENTAL',('LIST_PROTOCOL',),85,300,25,'LEFT','NONE',(135,200,945,1120),'Three practical steps; consistent numbering and generous spacing.'),
    'QUOTE_WHISPER': ComponentSpec('QUOTE_WHISPER','EXPERIMENTAL',('INSIGHT_WHISPER',),80,190,60,'CENTER','WHISPER_ALLOWED',(140,260,940,1080),'Quiet insight with optional italic/foil whisper.'),
    'ONE_LINE_INSIGHT': ComponentSpec('ONE_LINE_INSIGHT','EXPERIMENTAL',('INSIGHT_WHISPER','INNER_EXPLAIN'),95,80,45,'CENTER','OPTIONAL_SMALL',(140,270,940,1030),'Extreme negative space around one strong thought.'),
    'EVIDENCE_CARD': ComponentSpec('EVIDENCE_CARD','EXPERIMENTAL',('EVIDENCE',),90,320,22,'LEFT','NONE',(130,190,950,1130),'Editorial evidence layout, not a generic UI card aesthetic.'),
    'CTA_FOLLOW': ComponentSpec('CTA_FOLLOW','EXPERIMENTAL',('CTA',),90,190,28,'CENTER','OPTIONAL_SMALL',(130,260,950,1080),'Follow CTA focused on future value.'),
    'CTA_SAVE': ComponentSpec('CTA_SAVE','EXPERIMENTAL',('CTA',),90,190,28,'CENTER','OPTIONAL_SMALL',(130,260,950,1080),'Save CTA for reference-value content.'),
    'CTA_COMMENT': ComponentSpec('CTA_COMMENT','EXPERIMENTAL',('CTA',),90,190,28,'CENTER','OPTIONAL_SMALL',(130,260,950,1080),'Comment CTA only when genuine discussion fits.'),
}


def get_component(component_id: str, *, allow_experimental: bool=False) -> ComponentSpec:
    cid=str(component_id or '').strip().upper()
    if cid not in COMPONENTS: raise KeyError('COMPONENT_NOT_FOUND')
    spec=COMPONENTS[cid]
    if spec.status=='RETIRED': raise PermissionError('COMPONENT_RETIRED')
    if spec.status!='ACTIVE' and not allow_experimental: raise PermissionError('COMPONENT_NOT_ACTIVE')
    return spec


def validate_assignment(component_id: str, slide: Mapping[str,object], *, allow_experimental: bool=False) -> ComponentSpec:
    spec=get_component(component_id,allow_experimental=allow_experimental)
    role=str(slide.get('role') or '').strip().upper()
    if role not in VALID_ROLES: raise ValueError('SLIDE_ROLE_INVALID')
    if role not in spec.roles: raise ValueError('COMPONENT_ROLE_MISMATCH')
    headline=str(slide.get('headline') or '')
    body=str(slide.get('body') or '')
    hook=str(slide.get('hook') or '')
    if len(headline)>spec.max_headline_chars or len(body)>spec.max_body_chars or len(hook)>spec.max_hook_chars:
        raise ValueError('COPY_DENSITY_CONFLICT')
    if spec.foil_policy=='NONE' and hook.strip(): raise ValueError('COMPONENT_FOIL_NOT_ALLOWED')
    return spec


def activate_component(component_id: str, *, human_approved: bool=False) -> ComponentSpec:
    if not human_approved: raise PermissionError('HUMAN_VISUAL_APPROVAL_REQUIRED')
    cid=str(component_id or '').strip().upper()
    if cid not in COMPONENTS: raise KeyError('COMPONENT_NOT_FOUND')
    spec=COMPONENTS[cid]
    if spec.status=='RETIRED': raise PermissionError('COMPONENT_RETIRED')
    return ComponentSpec(**{**spec.__dict__,'status':'ACTIVE'})
