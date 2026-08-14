from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from PIL import Image, ImageChops, ImageStat

GOLDEN_COLUMNS=[
    'golden_id','accepted_at','archive_id','asset_id','master_id','platform','output_type','role_or_series','quality_reason',
    'component_tags','baseline_renderer_version','baseline_manifest_ref','status','superseded_by','notes',
]

@dataclass(frozen=True)
class GoldenRecord:
    golden_id: str
    accepted_at: str
    archive_id: str
    asset_id: str
    master_id: str
    platform: str
    output_type: str
    role_or_series: str
    quality_reason: str
    component_tags: str
    baseline_renderer_version: str
    baseline_manifest_ref: str
    status: str
    superseded_by: str
    notes: str

    def to_row(self)->list[object]:
        return [getattr(self,c) for c in GOLDEN_COLUMNS]

@dataclass(frozen=True)
class RegressionResult:
    status: str
    baseline_count: int
    candidate_count: int
    dimension_pass: bool
    exact_file_matches: int
    changed_files: int
    mean_pixel_delta: float | None
    reason: str
    human_review_required: bool


def sha256_file(path: str|Path)->str:
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def create_golden_candidate(*,golden_id:str,now:datetime,archive_id:str,asset_id:str,master_id:str,platform:str,output_type:str,role_or_series:str,quality_reason:str,baseline_renderer_version:str,baseline_manifest_ref:str,component_tags:str='',notes:str='',human_nominated:bool=False)->GoldenRecord:
    if not human_nominated: raise PermissionError('HUMAN_GOLDEN_NOMINATION_REQUIRED')
    if not archive_id.strip() or not asset_id.strip() or not master_id.strip(): raise ValueError('GOLDEN_SOURCE_REQUIRED')
    if not quality_reason.strip(): raise ValueError('GOLDEN_QUALITY_REASON_REQUIRED')
    if not baseline_manifest_ref.strip(): raise ValueError('GOLDEN_MANIFEST_REQUIRED')
    return GoldenRecord(golden_id,now.isoformat(),archive_id,asset_id,master_id,platform.upper(),output_type.upper(),role_or_series.upper(),quality_reason.strip(),component_tags.strip(),baseline_renderer_version.strip(),baseline_manifest_ref.strip(),'CANDIDATE','',''+notes)


def activate_golden(record:GoldenRecord,*,human_approved:bool=False,archive_verified:bool=False)->GoldenRecord:
    if not human_approved: raise PermissionError('HUMAN_GOLDEN_APPROVAL_REQUIRED')
    if not archive_verified: raise PermissionError('GOLDEN_ARCHIVE_VERIFY_REQUIRED')
    if record.status!='CANDIDATE': raise PermissionError('GOLDEN_STATUS_INVALID')
    return replace(record,status='ACTIVE')


def supersede_golden(record:GoldenRecord,new_golden_id:str,*,human_approved:bool=False)->GoldenRecord:
    if not human_approved: raise PermissionError('HUMAN_GOLDEN_APPROVAL_REQUIRED')
    if record.status!='ACTIVE': raise PermissionError('GOLDEN_STATUS_INVALID')
    if not new_golden_id.strip(): raise ValueError('GOLDEN_SUPERSEDE_REF_REQUIRED')
    return replace(record,status='SUPERSEDED',superseded_by=new_golden_id.strip())


def _pixel_delta(a:Path,b:Path)->float:
    ia=Image.open(a).convert('RGB'); ib=Image.open(b).convert('RGB')
    if ia.size!=ib.size: return 100.0
    diff=ImageChops.difference(ia,ib)
    stat=ImageStat.Stat(diff)
    return round(sum(stat.mean)/(3*255)*100,4)


def compare_series(baseline_files:Sequence[str|Path],candidate_files:Sequence[str|Path],*,expected_size:tuple[int,int],copy_fingerprint_equal:bool=True,canonical_assets_equal:bool=True,intended_visual_change:bool=False,human_visual_approved:bool=False)->RegressionResult:
    base=[Path(p) for p in baseline_files]; cand=[Path(p) for p in candidate_files]
    if len(base)!=len(cand):
        return RegressionResult('VISUAL_REGRESSION_FAIL',len(base),len(cand),False,0,abs(len(base)-len(cand)),None,'series count changed',False)
    if not copy_fingerprint_equal:
        return RegressionResult('VISUAL_REGRESSION_FAIL',len(base),len(cand),False,0,len(base),None,'copy fingerprint changed during visual regression',False)
    if not canonical_assets_equal:
        return RegressionResult('VISUAL_REGRESSION_FAIL',len(base),len(cand),False,0,len(base),None,'canonical asset identity changed',False)
    exact=0; deltas=[]
    for a,b in zip(base,cand):
        if not a.exists() or not b.exists():
            return RegressionResult('VISUAL_REGRESSION_FAIL',len(base),len(cand),False,exact,len(base)-exact,None,'missing regression file',False)
        if Image.open(a).size!=expected_size or Image.open(b).size!=expected_size:
            return RegressionResult('VISUAL_REGRESSION_FAIL',len(base),len(cand),False,exact,len(base)-exact,None,'dimension drift',False)
        if sha256_file(a)==sha256_file(b): exact+=1
        else: deltas.append(_pixel_delta(a,b))
    changed=len(base)-exact
    mean_delta=round(sum(deltas)/len(deltas),4) if deltas else 0.0
    if changed==0:
        return RegressionResult('PASS_EXACT',len(base),len(cand),True,exact,0,0.0,'exact deterministic match',False)
    if not intended_visual_change:
        return RegressionResult('HUMAN_REVIEW',len(base),len(cand),True,exact,changed,mean_delta,'unexpected visual pixel drift; objective gates pass but appearance changed',True)
    if not human_visual_approved:
        return RegressionResult('HUMAN_REVIEW',len(base),len(cand),True,exact,changed,mean_delta,'declared visual redesign requires human comparison/approval',True)
    return RegressionResult('PASS_APPROVED_CHANGE',len(base),len(cand),True,exact,changed,mean_delta,'declared visual change approved by human after objective gates passed',False)
