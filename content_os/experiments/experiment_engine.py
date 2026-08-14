from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Sequence

from content_os.performance.objective_engine import ObjectiveResult, compare_results

EXPERIMENT_COLUMNS=['experiment_id','created_at','master_id','hypothesis','objective','primary_metric','platform','output_type','variant_a_asset_id','variant_b_asset_id','changed_dimension','control_notes','started_at','ended_at','sample_context','result','confidence','learning_id','status','notes']
VALID_DIMENSIONS={'HOOK','COVER','CTA','LENGTH','PACING','COMPONENT','STRUCTURE'}
VALID_DESIGNS={'OBSERVATIONAL','PLATFORM_RANDOMIZED'}

@dataclass(frozen=True)
class Experiment:
    experiment_id:str;created_at:str;master_id:str;hypothesis:str;objective:str;primary_metric:str;platform:str;output_type:str;variant_a_asset_id:str;variant_b_asset_id:str;changed_dimension:str;control_notes:str;started_at:str;ended_at:str;sample_context:str;result:str;confidence:str;learning_id:str;status:str;notes:str
    def to_row(self):return [getattr(self,c) for c in EXPERIMENT_COLUMNS]


def next_experiment_id(existing_ids:Sequence[str],now:datetime)->str:
    prefix=f'EXP-{now:%Y%m%d}-';nums=[]
    for raw in existing_ids:
        m=re.fullmatch(re.escape(prefix)+r'(\d{3})',str(raw or ''))
        if m:nums.append(int(m.group(1)))
    return f'{prefix}{max(nums,default=0)+1:03d}'


def create_experiment(*,experiment_id:str,now:datetime,master_id:str,hypothesis:str,objective:str,primary_metric:str,platform:str,output_type:str,variant_a_asset_id:str,variant_b_asset_id:str,changed_dimension:str,control_notes:str,master_approved:bool=False,claims_equal:bool=False)->Experiment:
    if not master_approved:raise PermissionError('MASTER_AUTHORITY_REQUIRED')
    if not claims_equal:raise PermissionError('EXPERIMENT_CLAIM_DRIFT')
    if not master_id.strip():raise ValueError('MASTER_REF_REQUIRED')
    if not hypothesis.strip():raise ValueError('EXPERIMENT_HYPOTHESIS_REQUIRED')
    if variant_a_asset_id==variant_b_asset_id or not variant_a_asset_id.strip() or not variant_b_asset_id.strip():raise ValueError('EXPERIMENT_VARIANTS_INVALID')
    dim=changed_dimension.upper().strip()
    if dim not in VALID_DIMENSIONS:raise ValueError('EXPERIMENT_DIMENSION_INVALID')
    if not control_notes.strip():raise ValueError('EXPERIMENT_CONTROL_REQUIRED')
    return Experiment(experiment_id,now.isoformat(),master_id,hypothesis.strip(),objective.upper(),primary_metric.upper(),platform.upper(),output_type.upper(),variant_a_asset_id,variant_b_asset_id,dim,control_notes.strip(),'','','','','','', 'PLANNED','One material packaging dimension should change; semantic thesis/claims remain fixed.')


def start_experiment(exp:Experiment,*,now:datetime,distribution_ready_a:bool=False,distribution_ready_b:bool=False)->Experiment:
    if exp.status!='PLANNED':raise PermissionError('EXPERIMENT_STATUS_INVALID')
    if not distribution_ready_a or not distribution_ready_b:raise PermissionError('DISTRIBUTION_AUTHORITY_REQUIRED')
    return replace(exp,status='RUNNING',started_at=now.isoformat())


def finish_experiment(exp:Experiment,*,now:datetime,result_a:ObjectiveResult,result_b:ObjectiveResult,sample_context:str,design:str='OBSERVATIONAL')->Experiment:
    if exp.status!='RUNNING':raise PermissionError('EXPERIMENT_STATUS_INVALID')
    design=design.upper().strip()
    if design not in VALID_DESIGNS:raise ValueError('EXPERIMENT_DESIGN_INVALID')
    if result_a.objective!=exp.objective or result_b.objective!=exp.objective:raise ValueError('OBJECTIVE_MISMATCH')
    if result_a.metric_key!=exp.primary_metric or result_b.metric_key!=exp.primary_metric:raise ValueError('EXPERIMENT_METRIC_MISMATCH')
    cmp=compare_results(result_a,result_b)
    if cmp['status']!='OK':
        result='INSUFFICIENT_DATA';confidence='LOW'
    else:
        delta=cmp['delta'];direction=cmp['direction']
        result=f'DESCRIPTIVE_SIGNAL: variant B vs A {direction} {delta:+.4f} percentage points on {exp.primary_metric}'
        confidence='MEDIUM' if design=='PLATFORM_RANDOMIZED' else 'LOW'
    note='Organic/observational comparison is not causal proof. Even PLATFORM_RANDOMIZED remains descriptive here until a separate statistical-significance contract exists.'
    return replace(exp,status='COMPLETE',ended_at=now.isoformat(),sample_context=sample_context.strip(),result=result,confidence=confidence,notes=exp.notes+' | '+note)


def link_learning(exp:Experiment,learning_id:str)->Experiment:
    if exp.status!='COMPLETE':raise PermissionError('EXPERIMENT_STATUS_INVALID')
    if not learning_id.strip():raise ValueError('LEARNING_REF_REQUIRED')
    return replace(exp,learning_id=learning_id.strip())
