from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

VALID_OBJECTIVES={'FOLLOW','SAVE','SHARE','COMMENT','TRUST','CONVERT'}

@dataclass(frozen=True)
class ObjectiveResult:
    objective: str
    metric_key: str
    value: float | None
    numerator_key: str
    denominator_key: str
    numerator: float | None
    denominator: float | None
    status: str
    reason: str


def _num(metrics:Mapping[str,object],key:str)->float|None:
    v=metrics.get(key)
    if v in (None,''): return None
    try:return float(v)
    except (TypeError,ValueError):return None


def _rate(objective:str,metric_key:str,metrics:Mapping[str,object],num_key:str,den_key:str)->ObjectiveResult:
    n=_num(metrics,num_key);d=_num(metrics,den_key)
    if n is None or d is None:
        return ObjectiveResult(objective,metric_key,None,num_key,den_key,n,d,'UNKNOWN','required numerator/denominator missing')
    if d<=0:
        return ObjectiveResult(objective,metric_key,None,num_key,den_key,n,d,'UNKNOWN','denominator is zero/nonpositive; rate remains unknown')
    return ObjectiveResult(objective,metric_key,round(n/d*100,4),num_key,den_key,n,d,'OK','rate calculated from explicit numerator and denominator')


def evaluate_objective(objective:str,metrics:Mapping[str,object],*,trust_proxy_key:str='',conversion_numerator_key:str='',conversion_denominator_key:str='')->ObjectiveResult:
    obj=str(objective or '').strip().upper()
    if obj not in VALID_OBJECTIVES: raise ValueError('OBJECTIVE_INVALID')
    gate=str(metrics.get('metric_integrity_gate') or '').strip().upper()
    if gate and gate!='OK': raise PermissionError('METRIC_INTEGRITY_FAIL')
    if obj=='FOLLOW': return _rate(obj,'FOLLOW_RATE',metrics,'follows','profile_visits')
    if obj=='SAVE': return _rate(obj,'SAVE_RATE',metrics,'saves','reach')
    if obj=='SHARE': return _rate(obj,'SHARE_RATE',metrics,'shares','reach')
    if obj=='COMMENT': return _rate(obj,'COMMENT_RATE',metrics,'comments','reach')
    if obj=='TRUST':
        proxy=str(trust_proxy_key or '').strip()
        if not proxy: raise ValueError('TRUST_PROXY_REQUIRED')
        v=_num(metrics,proxy)
        if v is None: return ObjectiveResult(obj,'TRUST_PROXY',None,proxy,'',v,None,'UNKNOWN','declared trust proxy unavailable')
        return ObjectiveResult(obj,'TRUST_PROXY',v,proxy,'',v,None,'OK',f'explicit proxy={proxy}; proxy is not direct trust measurement')
    num=str(conversion_numerator_key or '').strip();den=str(conversion_denominator_key or '').strip()
    if not num or not den: raise ValueError('CONVERSION_DEFINITION_REQUIRED')
    return _rate(obj,'CONVERSION_RATE',metrics,num,den)


def compare_results(a:ObjectiveResult,b:ObjectiveResult)->dict[str,object]:
    if a.objective!=b.objective or a.metric_key!=b.metric_key: raise ValueError('OBJECTIVE_MISMATCH')
    if a.status!='OK' or b.status!='OK' or a.value is None or b.value is None:
        return {'status':'INSUFFICIENT_DATA','delta':None,'reason':'both comparable objective results must be OK'}
    return {'status':'OK','delta':round(b.value-a.value,4),'direction':'UP' if b.value>a.value else ('DOWN' if b.value<a.value else 'FLAT'),'metric_key':a.metric_key}
