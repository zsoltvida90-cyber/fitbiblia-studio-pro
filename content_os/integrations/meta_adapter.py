import hashlib, json, re
from datetime import datetime, timezone

SECRET_KEYS = {'access_token','app_secret','client_secret','token','authorization','bearer_token','refresh_token'}

def _secret_key(key):
    norm = re.sub(r'[^a-z0-9]+', '_', str(key).lower()).strip('_')
    return norm in SECRET_KEYS or norm.endswith('_token') or norm.endswith('_secret') or norm.startswith('authorization')

def assert_no_secrets(payload):
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if _secret_key(k):
                    raise ValueError('SECRET_IN_PAYLOAD')
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(payload)
    return True

def event_key(event):
    if event.get('event_id'):
        return str(event['event_id'])
    parts = [event.get('account_key',''), event.get('external_media_id',''), event.get('event_type',''), event.get('observed_at',''), event.get('metric_name','')]
    if not any(str(x).strip() for x in parts):
        raise ValueError('EVENT_KEY_FIELDS_REQUIRED')
    return hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:32]

def normalize_insights_response(data, asset_id, external_media_id='', raw_ingest_ref='', source_system='META_API', captured_at=None):
    if not str(asset_id).strip():
        raise ValueError('ASSET_REQUIRED')
    if not raw_ingest_ref:
        raise ValueError('RAW_REF_REQUIRED')
    assert_no_secrets(data)
    captured_at = captured_at or datetime.now(timezone.utc).isoformat()
    metrics = {}
    for item in (data or {}).get('data', []):
        name = item.get('name')
        values = item.get('values') or []
        metrics[name] = (values[-1].get('value') if values else None) if name else None
    out = {'asset_id':asset_id,'platform':'INSTAGRAM','external_media_id':external_media_id,'captured_at':captured_at,'source_system':source_system,'raw_ingest_ref':raw_ingest_ref}
    mapping = {'reach':'reach','impressions':'impressions','views':'views','plays':'views','likes':'likes','comments':'comments','saved':'saves','shares':'shares','profile_visits':'profile_visits','follows':'follows','ig_reels_video_view_total_time':'watch_time_seconds','ig_reels_avg_watch_time':'avg_watch_time_seconds'}
    for source_name, target_name in mapping.items():
        if source_name in metrics and target_name not in out:
            out[target_name] = metrics[source_name]
    return out

def normalize_webhook(event, account_key, raw_ingest_ref):
    if not str(account_key).strip():
        raise ValueError('ACCOUNT_REQUIRED')
    if not str(raw_ingest_ref).strip():
        raise ValueError('RAW_REF_REQUIRED')
    assert_no_secrets(event)
    event_type = event.get('field') or event.get('event_type')
    if not str(event_type or '').strip():
        raise ValueError('EVENT_TYPE_REQUIRED')
    observed = event.get('time') or event.get('observed_at') or datetime.now(timezone.utc).isoformat()
    keyed = {**event, 'account_key':account_key, 'event_type':event_type, 'observed_at':observed}
    return {
        'event_id': event_key(keyed),
        'event_type': event_type,
        'object_type': event.get('object','instagram'),
        'account_key': account_key,
        'external_media_id': str(event.get('media_id') or event.get('external_media_id') or ''),
        'observed_at': str(observed),
        'source_system':'META_WEBHOOK',
        'raw_ingest_ref':raw_ingest_ref,
        'payload_digest':hashlib.sha256(json.dumps(event,sort_keys=True,default=str).encode()).hexdigest()
    }

def upsert_decision(existing_event_ids, event):
    key = event_key(event)
    return {'event_id':key,'action':'IGNORE_DUPLICATE' if key in set(existing_event_ids) else 'APPEND'}
