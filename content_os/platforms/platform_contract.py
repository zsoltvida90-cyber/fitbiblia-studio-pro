from __future__ import annotations
import unicodedata,re
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
def build_x_post(text,char_limit=X_STANDARD_CHAR_LIMIT):
 text=str(text or '').strip()
 if not text:raise ValueError('X_POST_TEXT_REQUIRED')
 if len(text)>char_limit:raise ValueError('X_POST_TOO_LONG')
 return {'format':'X_POST','target_platform':'X','execution_state':'TEXT_READY','text':text,'character_count':len(text),'character_limit':char_limit}
def build_x_thread(posts,char_limit=X_STANDARD_CHAR_LIMIT):
 posts=[str(x or '').strip() for x in (posts or [])]
 if len(posts)<2:raise ValueError('X_THREAD_MIN_POSTS')
 if any(not p for p in posts):raise ValueError('X_THREAD_EMPTY_POST')
 if any(len(p)>char_limit for p in posts):raise ValueError('X_POST_TOO_LONG')
 return {'format':'X_THREAD','target_platform':'X','execution_state':'TEXT_READY','posts':[{'index':i,'text':p,'character_count':len(p)} for i,p in enumerate(posts,1)],'character_limit':char_limit}
def validate_platform_output(platform,output_type):
 p=normalize_platform(platform);o=str(output_type or '').upper();allowed={'INSTAGRAM':{'CAROUSEL','STORY','STATIC_POST','REEL','CAPTION'},'TIKTOK':{'REEL','CAPTION'},'X':{'X_POST','X_THREAD'},'FACEBOOK':{'STATIC_POST','REEL','CAPTION'},'YOUTUBE_SHORTS':{'REEL'}}
 return {'platform':p,'output_type':o,'compatible':o in allowed.get(p,set())}
