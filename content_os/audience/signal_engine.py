from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Iterable, Mapping, Sequence

SIGNAL_COLUMNS=['signal_id','captured_at','source_type','source_ref','text_summary','normalized_problem','persona_candidate','topic_domain','intent_type','cluster_key','recurrence_state','confidence','status','linked_idea_id','notes']
VALID_SOURCE_TYPES={'COMMENT','DM','POLL','EMAIL','SEARCH','FORM','META','MANUAL'}
VALID_INTENTS={'QUESTION','PAIN','OBJECTION','GOAL','CONFUSION','REQUEST','BELIEF','OTHER'}
VALID_STATES={'ONE_OFF','RECURRING','VALIDATED_PATTERN'}

@dataclass(frozen=True)
class AudienceSignal:
    signal_id:str;captured_at:str;source_type:str;source_ref:str;text_summary:str;normalized_problem:str;persona_candidate:str;topic_domain:str;intent_type:str;cluster_key:str;recurrence_state:str;confidence:str;status:str;linked_idea_id:str;notes:str
    def to_row(self):return [getattr(self,c) for c in SIGNAL_COLUMNS]

@dataclass(frozen=True)
class AudienceCluster:
    cluster_key:str;signal_count:int;unique_sources:int;state:str;confidence:str;topic_domain:str;normalized_problem:str;persona_candidates:tuple[str,...];reason:str

EMAIL_RE=re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',re.I)
PHONE_RE=re.compile(r'(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)')
HANDLE_RE=re.compile(r'(?<!\w)@[A-Za-z0-9_.-]{2,}')
URL_RE=re.compile(r'https?://\S+|www\.\S+',re.I)


def _norm(text:str)->str:
    text=unicodedata.normalize('NFKD',str(text or ''))
    text=''.join(c for c in text if not unicodedata.combining(c)).lower()
    return ' '.join(re.findall(r'[a-z0-9]+',text))


def sanitize_summary(text:str,max_chars:int=280)->str:
    text=' '.join(str(text or '').split())
    text=EMAIL_RE.sub('[email]',text);text=PHONE_RE.sub('[phone]',text);text=HANDLE_RE.sub('[handle]',text);text=URL_RE.sub('[url]',text)
    if len(text)>max_chars:text=text[:max_chars-1].rstrip()+'…'
    return text


def safe_source_ref(source_ref:str)->str:
    ref=str(source_ref or '').strip()
    if not ref:return ''
    if EMAIL_RE.search(ref) or PHONE_RE.search(ref) or HANDLE_RE.search(ref) or '://' in ref:
        return 'anon:'+hashlib.sha256(ref.encode('utf-8')).hexdigest()[:16]
    return ref[:160]


def cluster_key(topic_domain:str,normalized_problem:str)->str:
    base=_norm(topic_domain)+'|'+_norm(normalized_problem)
    if not _norm(normalized_problem):raise ValueError('AUDIENCE_PROBLEM_REQUIRED')
    return hashlib.sha256(base.encode('utf-8')).hexdigest()[:16]


def next_signal_id(existing_ids:Sequence[str],now:datetime)->str:
    prefix=f'SIG-{now:%Y%m%d}-';nums=[]
    for raw in existing_ids:
        m=re.fullmatch(re.escape(prefix)+r'(\d{3})',str(raw or ''))
        if m:nums.append(int(m.group(1)))
    return f'{prefix}{max(nums,default=0)+1:03d}'


def create_signal(*,signal_id:str,now:datetime,source_type:str,source_ref:str,text_summary:str,normalized_problem:str,topic_domain:str,intent_type:str='OTHER',persona_candidate:str='',notes:str='')->AudienceSignal:
    st=source_type.upper().strip();intent=intent_type.upper().strip()
    if st not in VALID_SOURCE_TYPES:raise ValueError('AUDIENCE_SOURCE_INVALID')
    if intent not in VALID_INTENTS:raise ValueError('AUDIENCE_INTENT_INVALID')
    summary=sanitize_summary(text_summary)
    if not summary:raise ValueError('AUDIENCE_SUMMARY_REQUIRED')
    key=cluster_key(topic_domain,normalized_problem)
    return AudienceSignal(signal_id,now.isoformat(),st,safe_source_ref(source_ref),summary,normalized_problem.strip(),persona_candidate.upper().strip(),topic_domain.upper().strip(),intent,key,'ONE_OFF','LOW','ACTIVE','',notes)


def cluster_signals(signals:Iterable[Mapping[str,object]],*,recurring_min:int=3,validated_min:int=10,validated_min_sources:int=5)->list[AudienceCluster]:
    groups={}
    for s in signals:
        if str(s.get('status') or 'ACTIVE').upper()!='ACTIVE':continue
        key=str(s.get('cluster_key') or '').strip()
        if not key:continue
        groups.setdefault(key,[]).append(s)
    out=[]
    for key,grp in groups.items():
        refs={str(s.get('source_ref') or '').strip() for s in grp if str(s.get('source_ref') or '').strip()}
        n=len(grp);u=len(refs)
        if n>=validated_min and u>=validated_min_sources:state,conf='VALIDATED_PATTERN','HIGH'
        elif n>=recurring_min:state,conf='RECURRING','MEDIUM'
        else:state,conf='ONE_OFF','LOW'
        first=grp[0];personas=tuple(sorted({str(s.get('persona_candidate') or '').strip().upper() for s in grp if str(s.get('persona_candidate') or '').strip()}))
        out.append(AudienceCluster(key,n,u,state,conf,str(first.get('topic_domain') or '').upper(),str(first.get('normalized_problem') or ''),personas,f'{n} signals across {u} unique source refs'))
    return sorted(out,key=lambda x:(-x.signal_count,x.cluster_key))


def apply_cluster_state(signal:AudienceSignal,cluster:AudienceCluster)->AudienceSignal:
    if signal.cluster_key!=cluster.cluster_key:raise ValueError('AUDIENCE_CLUSTER_MISMATCH')
    return replace(signal,recurrence_state=cluster.state,confidence=cluster.confidence)


def idea_seed(cluster:AudienceCluster)->dict[str,object]:
    if cluster.state=='ONE_OFF':raise PermissionError('AUDIENCE_PATTERN_INSUFFICIENT')
    return {'source_type':'AUDIENCE_SIGNAL','source_ref':f'audience-cluster://{cluster.cluster_key}','topic_domain':cluster.topic_domain,'problem':cluster.normalized_problem,'persona':'GENERAL','why_now':f'{cluster.state}: {cluster.signal_count} signals / {cluster.unique_sources} sources','evidence_readiness':'UNKNOWN','notes':'Audience demand signal only; Radar/Science gates still required.'}
