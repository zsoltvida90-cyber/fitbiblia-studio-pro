from __future__ import annotations
import unicodedata,re
try:
    from twitter_text import parse_tweet as _parse_tweet
except Exception:
    _parse_tweet = None
PLATFORM_ALIASES={'instagram':'INSTAGRAM','insta':'INSTAGRAM','ig':'INSTAGRAM','tiktok':'TIKTOK','tik tok':'TIKTOK','x':'X','twitter':'X','facebook':'FACEBOOK','fb':'FACEBOOK','youtube shorts':'YOUTUBE_SHORTS','shorts':'YOUTUBE_SHORTS'}
X_STANDARD_CHAR_LIMIT=280
def _norm(s):
    s=unicodedata.normalize('NFKD',str(s or ''));s=''.join(c for c in s if not unicodedata.combining(c));s=s.lower().strip();return re.sub(r'\s+',' ',s)
def normalize_platform(value):
    n=_norm(value)
    if not n:return 'UNSPECIFIED'
    if n.upper() in {'INSTAGRAM','TIKTOK','X','FACEBOOK','YOUTUBE_SHORTS'}:return n.upper()
    if n in PLATFORM_ALIASES:return PLATFORM_ALIASES[n]
    raise ValueError('PLATFORM_UNSUPPORTED')
def _result_value(result,key):
    if hasattr(result,key):return getattr(result,key)
    if hasattr(result,'asdict'):return result.asdict().get(key)
    if isinstance(result,dict):return result.get(key)
    return None
def _latin_safe_fallback(text):
    text=unicodedata.normalize('NFC',text)
    if re.search(r'https?://|www\.',text,re.I):raise RuntimeError('X_WEIGHTED_COUNTER_REQUIRED')
    for ch in text:
        cat=unicodedata.category(ch);name=unicodedata.name(ch,'')
        if ch.isspace() or cat[0] in {'P','N'}:continue
        if cat[0]=='L' and 'LATIN' in name:continue
        raise RuntimeError('X_WEIGHTED_COUNTER_REQUIRED')
    return len(text)
def x_weighted_length(text):
    text=unicodedata.normalize('NFC',str(text or ''))
    if _parse_tweet is not None:
        parsed=_parse_tweet(text);weighted=_result_value(parsed,'weightedLength');valid=_result_value(parsed,'valid')
        if weighted is None:raise RuntimeError('X_WEIGHTED_COUNTER_INVALID')
        return int(weighted),bool(valid),'TWITTER_TEXT_CONFORMANCE'
    weighted=_latin_safe_fallback(text)
    return weighted,weighted<=X_STANDARD_CHAR_LIMIT,'LATIN_SAFE_FALLBACK'
def build_x_post(text,char_limit=X_STANDARD_CHAR_LIMIT):
    text=str(text or '').strip()
    if not text:raise ValueError('X_POST_TEXT_REQUIRED')
    count,valid,mode=x_weighted_length(text)
    if count>char_limit or not valid:raise ValueError('X_POST_TOO_LONG')
    return {'format':'X_POST','target_platform':'X','execution_state':'TEXT_READY','text':text,'character_count':count,'character_limit':char_limit,'count_mode':mode}
def build_x_thread(posts,char_limit=X_STANDARD_CHAR_LIMIT):
    posts=[str(x or '').strip() for x in (posts or [])]
    if len(posts)<2:raise ValueError('X_THREAD_MIN_POSTS')
    if any(not p for p in posts):raise ValueError('X_THREAD_EMPTY_POST')
    built=[]
    for i,p in enumerate(posts,1):
        count,valid,mode=x_weighted_length(p)
        if count>char_limit or not valid:raise ValueError('X_POST_TOO_LONG')
        built.append({'index':i,'text':p,'character_count':count,'count_mode':mode})
    return {'format':'X_THREAD','target_platform':'X','execution_state':'TEXT_READY','posts':built,'character_limit':char_limit}
def validate_platform_output(platform,output_type):
    p=normalize_platform(platform);o=str(output_type or '').upper();allowed={'INSTAGRAM':{'CAROUSEL','STORY','STATIC_POST','REEL','CAPTION'},'TIKTOK':{'REEL','CAPTION'},'X':{'X_POST','X_THREAD'},'FACEBOOK':{'STATIC_POST','REEL','CAPTION'},'YOUTUBE_SHORTS':{'REEL'}}
    return {'platform':p,'output_type':o,'compatible':o in allowed.get(p,set())}
