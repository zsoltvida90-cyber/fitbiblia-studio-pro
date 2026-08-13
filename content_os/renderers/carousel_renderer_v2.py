import json
from pathlib import Path
from PIL import Image,ImageDraw
from .render_primitives import *
ALLOWED_ROLES={'COVER','INNER_EXPLAIN','MECHANISM','MYTH','LIST_PROTOCOL','INSIGHT_WHISPER','EVIDENCE','CTA'}
def density_guard(s):
 role=s.get('role','INNER_EXPLAIN')
 if role not in ALLOWED_ROLES:raise RenderError(f'SLIDE_ROLE_INVALID:{role}')
 if len((s.get('body')or'').strip())+len((s.get('headline')or'').strip())>(130 if role=='COVER' else 350):raise RenderError('COPY_DENSITY_CONFLICT')
def render_slide(s,root,is_last=False):
 density_guard(s);base=cover_crop(Image.open(Path(root)/'assets/background.jpg')).convert('RGBA');d=ImageDraw.Draw(base);role=s.get('role','INNER_EXPLAIN');h=(s.get('headline')or'').strip();body=(s.get('body')or'').strip();hook=(s.get('hook')or'').strip()
 if role=='COVER':
  if h:
   _,lines=draw_text_block(d,(540,330),h,font(root,'semibold',58),max_width=850,line_gap=8,anchor='ma')
   if len(lines)>3:raise RenderError('COPY_DENSITY_CONFLICT')
  if hook:foil_text(base,root,hook,(540,640),150,900)
  if body:draw_text_block(d,(540,820),body,font(root,'regular',34),max_width=760,line_gap=8,anchor='ma')
 elif role=='INSIGHT_WHISPER':
  if h:draw_text_block(d,(540,460),h,font(root,'semibold',44),max_width=760,line_gap=8,anchor='ma')
  if body:draw_text_block(d,(540,665),body,font(root,'regular',31),max_width=760,line_gap=11,anchor='ma')
  if hook:foil_text(base,root,hook,(540,850),92,760)
 elif role=='CTA':
  if h:draw_text_block(d,(540,480),h,font(root,'semibold',48),max_width=790,line_gap=9,anchor='ma')
  if body:draw_text_block(d,(540,680),body,font(root,'regular',31),max_width=760,line_gap=10,anchor='ma')
 else:
  if h:draw_text_block(d,(540,365),h,font(root,'semibold',43),max_width=820,line_gap=8,anchor='ma')
  if body:
   y,_=draw_text_block(d,(540,555),body,font(root,'regular',31),max_width=820,line_gap=11,anchor='ma')
   if y>1070:raise RenderError('COPY_DENSITY_CONFLICT')
  if hook:foil_text(base,root,hook,(540,900),88,720)
 if role!='COVER':paste_logo(base,root)
 if not is_last:chevron(d)
 return base.convert('RGB')
def render_carousel(job,root,out_dir):
 m=load_manifest(root);slides=job.get('slides')or[]
 if not slides:raise RenderError('SERIES_INCOMPLETE')
 out_dir=Path(out_dir);out_dir.mkdir(parents=True,exist_ok=True);outs=[]
 for i,s in enumerate(slides,1):
  if s.get('slide_number',i)!=i:raise RenderError('SERIES_INCOMPLETE')
  p=out_dir/f'slide_{i:02d}.png';render_slide(s,root,i==len(slides)).save(p,'PNG',optimize=True);outs.append(str(p))
 result={'format':'CAROUSEL','renderer_version':'1.1.0','expected_slides':len(slides),'rendered_slides':len(outs),'outputs':outs,'asset_manifest_version':m['version']};(out_dir/'render_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');return result
