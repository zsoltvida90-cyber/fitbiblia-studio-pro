from __future__ import annotations
import hashlib, re, unicodedata
from datetime import date, datetime
from pathlib import Path

ALLOWED_STATUS = {'DRAFT','ACTIVE','SUPERSEDED','ARCHIVED'}
ALLOWED_REUSABLE = {'YES','NO'}

def sha256_file(path):
    h = hashlib.sha256(); path = Path(path)
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def _slug(text):
    text = unicodedata.normalize('NFKD', text or '')
    text = ''.join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return (re.sub(r'[^a-z0-9]+','-',text).strip('-')[:72] or 'research')

def bundle_filename(research_id, topic):
    if not re.fullmatch(r'RSH-\d{8}-\d{3}', research_id or ''):
        raise ValueError('INVALID_RESEARCH_ID')
    return f'{research_id}__{_slug(topic)}.txt'

def classify_freshness(reusable, review_due, today=None):
    if str(reusable).upper() != 'YES':
        return 'NOT_APPLICABLE'
    if not review_due:
        return 'REVIEW_DATE_REQUIRED'
    today = today or date.today()
    if isinstance(review_due, str):
        try:
            review_due = datetime.fromisoformat(review_due[:10]).date()
        except Exception:
            return 'REVIEW_DATE_INVALID'
    return 'REVIEW_DUE' if review_due < today else 'FRESH'

def validate_index_record(record):
    rid = str(record.get('research_id') or '').strip()
    if not rid: return 'RESEARCH_ID_REQUIRED'
    if not re.fullmatch(r'RSH-\d{8}-\d{3}', rid): return 'INVALID_RESEARCH_ID'
    if not str(record.get('project') or '').strip(): return 'PROJECT_REQUIRED'
    if not str(record.get('topic') or '').strip(): return 'TOPIC_REQUIRED'
    if not str(record.get('research_question') or '').strip(): return 'QUESTION_REQUIRED'
    status = str(record.get('status') or '').upper()
    reusable = str(record.get('reusable') or '').upper()
    bundle_ref = str(record.get('bundle_ref') or '').strip()
    bundle_hash = str(record.get('bundle_sha256') or '').strip()
    if status not in ALLOWED_STATUS: return 'INVALID_STATUS'
    if reusable not in ALLOWED_REUSABLE: return 'INVALID_REUSABLE'
    if status in {'ACTIVE','SUPERSEDED'} and not bundle_ref: return 'BUNDLE_REF_REQUIRED'
    if reusable == 'YES' and not bundle_ref: return 'BUNDLE_REF_REQUIRED'
    if bundle_ref and not bundle_hash: return 'BUNDLE_HASH_REQUIRED'
    if bundle_hash and not re.fullmatch(r'[0-9a-fA-F]{64}', bundle_hash): return 'BUNDLE_HASH_INVALID'
    if not str(record.get('version') or '').strip(): return 'VERSION_REQUIRED'
    return 'OK'

def verify_bundle_hash(path, expected):
    if not re.fullmatch(r'[0-9a-fA-F]{64}', str(expected or '')):
        raise ValueError('BUNDLE_HASH_INVALID')
    if sha256_file(path) != str(expected).lower():
        raise ValueError('BUNDLE_HASH_MISMATCH')
    return True
