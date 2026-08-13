from __future__ import annotations
import hashlib,re,unicodedata
from datetime import date,datetime
from pathlib import Path

def sha256_file(path):
    h=hashlib.sha256(); path=Path(path)
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def _slug(text):
    text=unicodedata.normalize('NFKD',text or '')
    text=''.join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return (re.sub(r'[^a-z0-9]+','-',text).strip('-')[:72] or 'research')

def bundle_filename(research_id,topic):
    if not re.fullmatch(r'RSH-\d{8}-\d{3}',research_id or ''): raise ValueError('INVALID_RESEARCH_ID')
    return f'{research_id}__{_slug(topic)}.txt'

def classify_freshness(reusable,review_due,today=None):
    if str(reusable).upper()!='YES': return 'NOT_APPLICABLE'
    if not review_due: return 'REVIEW_DATE_REQUIRED'
    today=today or date.today()
    if isinstance(review_due,str): review_due=datetime.fromisoformat(review_due[:10]).date()
    return 'REVIEW_DUE' if review_due<today else 'FRESH'

def validate_index_record(r):
    rid=str(r.get('research_id') or '').strip()
    if not rid: return 'RESEARCH_ID_REQUIRED'
    if not re.fullmatch(r'RSH-\d{8}-\d{3}',rid): return 'INVALID_RESEARCH_ID'
    if not str(r.get('project') or '').strip(): return 'PROJECT_REQUIRED'
    if not str(r.get('topic') or '').strip(): return 'TOPIC_REQUIRED'
    if not str(r.get('research_question') or '').strip(): return 'QUESTION_REQUIRED'
    status=str(r.get('status') or '').upper(); bref=str(r.get('bundle_ref') or '').strip(); bhash=str(r.get('bundle_sha256') or '').strip(); reusable=str(r.get('reusable') or '').upper()
    if status in {'ACTIVE','SUPERSEDED'} and not bref: return 'BUNDLE_REF_REQUIRED'
    if reusable=='YES' and not bref: return 'BUNDLE_REF_REQUIRED'
    if bref and not bhash: return 'BUNDLE_HASH_REQUIRED'
    if not str(r.get('version') or '').strip(): return 'VERSION_REQUIRED'
    return 'OK'

def verify_bundle_hash(path,expected):
    if sha256_file(path)!=expected: raise ValueError('BUNDLE_HASH_MISMATCH')
    return True
