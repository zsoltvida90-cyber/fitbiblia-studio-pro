import hashlib,json
from datetime import datetime,timezone
SECRET_KEYS={'access_token','app_secret','client_secret','token','authorization'}
def assert_no_secrets(payload):
 def walk(x):
  if isinstance(x,dict):
   for k,v in x.items():
    if k.lower() in SECRET_KEYS: raise ValueError('SECRET_IN_PAYLOAD')
    walk(v)
  elif isinstance(x,list):
   for v in x: walk(v)
 walk(payload); return True
def event_key(e):
 if e.get('event_id'): return str(e['event_id'])
 p=[e.get('account_key',''),e.get('external_media_id',''),e.get('event_type',''),e.get('observed_at',''),e.get('metric_name','')]
 return hashlib.sha256('|'.join(p).encode()).hexdigest()[:32]
def normalize_insights_response(data,asset_id,external_media_id='',raw_ingest_ref='',source_system='META_API',captured_at=None):
 if not raw_ingest_ref: raise ValueError('RAW_REF_REQUIRED')
 captured_at=captured_at or datetime.now(timezone.utc).isoformat(); metrics={}
 for item in (data or {}).get('data',[]):
  name=item.get('name'); values=item.get('values') or []; metrics[name]=(values[-1].get('value') if values else None) if name else None
 out={'asset_id':asset_id,'platform':'INSTAGRAM','external_media_id':external_media_id,'captured_at':captured_at,'source_system':source_system,'raw_ingest_ref':raw_ingest_ref}
 mapping={'reach':'reach','impressions':'impressions','views':'views','plays':'views','likes':'likes','comments':'comments','saved':'saves','shares':'shares','profile_visits':'profile_visits','follows':'follows','ig_reels_video_view_total_time':'watch_time_seconds','ig_reels_avg_watch_time':'avg_watch_time_seconds'}
 for a,b in mapping.items():
  if a in metrics and b not in out: out[b]=metrics[a]
 return out
def normalize_webhook(event,account_key,raw_ingest_ref):
 assert_no_secrets(event); observed=event.get('time') or event.get('observed_at') or datetime.now(timezone.utc).isoformat()
 return {'event_id':event_key(event),'event_type':event.get('field') or event.get('event_type','unknown'),'object_type':event.get('object','instagram'),'account_key':account_key,'external_media_id':str(event.get('media_id') or event.get('external_media_id') or ''),'observed_at':str(observed),'source_system':'META_WEBHOOK','raw_ingest_ref':raw_ingest_ref,'payload_digest':hashlib.sha256(json.dumps(event,sort_keys=True,default=str).encode()).hexdigest()}
def upsert_decision(existing_event_ids,event):
 k=event_key(event); return {'event_id':k,'action':'IGNORE_DUPLICATE' if k in set(existing_event_ids) else 'APPEND'}
