from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from PIL import Image,ImageDraw
from .render_primitives import *
from .component_registry import validate_assignment
VERSION='3.0.0-candidate'

def copy_hash(s):
 raw='\n'.join([str(s.get('headline') or ''),str(s.get('hook') or ''),str(s.get('body') or '')])
 return hashlib.sha256(raw.encode('utf-8')).hexdigest()
def darken(base,alpha=46):
 veil=Image.new('RGBA',base.size,(0,0,0,alpha));return Image.alpha_composite(base,veil)
def base_canvas(root):
 with Image.open(Path(root)/'assets/background.jpg') as im: base=cover_crop(im).convert('RGBA')
 return darken(base)
def footer(base,root,is_last):
 d=ImageDraw.Draw(base);paste_logo(base,root,width=118,y=1252)
 if not is_last:chevron(d,x=1026,y=675,size=25,width=5)
def split_source(body):
 if '\n\nForrás:' in body:
  main,src=body.rsplit('\n\nForrás:',1);return main.strip(),'Forrás: '+src.strip()
 return body.strip(),''
def render_cover(s,root,is_last):
 base=base_canvas(root);d=ImageDraw.Draw(base);h=s.get('headline','');hook=s.get('hook','');body=s.get('body','')
 draw_text_block(d,(120,250),h,font(root,'semibold',66),max_width=790,line_gap=5,anchor='la')
 foil_text(base,root,hook,(540,650),128,850)
 draw_text_block(d,(120,850),body,font(root,'regular',32),max_width=700,line_gap=8,anchor='la')
 if not is_last:chevron(d,x=1026,y=675,size=25,width=5)
 return base
def render_inner(s,root,is_last):
 base=base_canvas(root);d=ImageDraw.Draw(base)
 draw_text_block(d,(120,285),s.get('headline',''),font(root,'semibold',50),max_width=790,line_gap=7,anchor='la')
 y,_=draw_text_block(d,(120,560),s.get('body',''),font(root,'regular',32),max_width=790,line_gap=12,anchor='la')
 if y>1080:raise RenderError('COPY_DENSITY_CONFLICT')
 footer(base,root,is_last);return base
def render_evidence(s,root,is_last):
 base=base_canvas(root);d=ImageDraw.Draw(base);stat=str(s.get('stat') or '').strip();main,src=split_source(str(s.get('body') or ''))
 if stat:foil_text(base,root,stat.lower(),(310,295),112,470)
 draw_text_block(d,(120,465),s.get('headline',''),font(root,'semibold',47),max_width=790,line_gap=7,anchor='la')
 y,_=draw_text_block(d,(120,650),main,font(root,'regular',30),max_width=790,line_gap=11,anchor='la')
 if y>1035:raise RenderError('COPY_DENSITY_CONFLICT')
 if src:draw_text_block(d,(120,1070),src,font(root,'regular',23),max_width=760,line_gap=6,anchor='la')
 footer(base,root,is_last);return base
def render_whisper(s,root,is_last):
 base=base_canvas(root);d=ImageDraw.Draw(base)
 draw_text_block(d,(120,300),s.get('headline',''),font(root,'semibold',50),max_width=780,line_gap=7,anchor='la')
 foil_text(base,root,s.get('hook',''),(540,635),82,760)
 y,_=draw_text_block(d,(120,790),s.get('body',''),font(root,'regular',31),max_width=790,line_gap=11,anchor='la')
 if y>1080:raise RenderError('COPY_DENSITY_CONFLICT')
 footer(base,root,is_last);return base
def render_protocol(s,root,is_last):
 base=base_canvas(root);d=ImageDraw.Draw(base)
 draw_text_block(d,(120,245),s.get('headline',''),font(root,'semibold',48),max_width=800,line_gap=7,anchor='la')
 blocks=[b.strip() for b in str(s.get('body') or '').split('\n\n') if b.strip()]
 y=520
 for b in blocks:
  m=re.match(r'^(\d{2})\s+(.*)$',b,re.S);num=m.group(1) if m else '';txt=m.group(2) if m else b
  if num:d.text((130,y),num,font=font(root,'semibold',48),fill=BONE,anchor='la')
  end,_=draw_text_block(d,(245,y+3),txt,font(root,'regular',30),max_width=680,line_gap=9,anchor='la')
  y=max(y+100,end+35)
 if y>1120:raise RenderError('COPY_DENSITY_CONFLICT')
 footer(base,root,is_last);return base
def render_cta(s,root,is_last):
 base=base_canvas(root);d=ImageDraw.Draw(base)
 draw_text_block(d,(540,390),s.get('headline',''),font(root,'semibold',54),max_width=820,line_gap=8,anchor='ma')
 draw_text_block(d,(540,720),s.get('body',''),font(root,'regular',31),max_width=760,line_gap=11,anchor='ma')
 paste_logo(base,root,width=128,y=1130)
 return base
RENDERERS={'COVER_BIG_HOOK':render_cover,'INNER_EXPLAIN':render_inner,'NUMBER_EVIDENCE':render_evidence,'QUOTE_WHISPER':render_whisper,'THREE_STEP_PROTOCOL':render_protocol,'CTA_FOLLOW':render_cta}
def render_slide(s,root,is_last=False):
 cid=str(s.get('component_id') or '').strip().upper();validate_assignment(cid,s,allow_experimental=True)
 if cid not in RENDERERS:raise RenderError('COMPONENT_NOT_IMPLEMENTED')
 return RENDERERS[cid](s,root,is_last).convert('RGB')
def render_carousel(job,root,out_dir):
 m=load_manifest(root);slides=job.get('slides') or []
 if not slides:raise RenderError('SERIES_INCOMPLETE')
 out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);files=[];components=[];hashes=[]
 for i,s in enumerate(slides,1):
  if s.get('slide_number',i)!=i:raise RenderError('SERIES_INCOMPLETE')
  p=out/f'slide_{i:02d}.png';render_slide(s,root,i==len(slides)).save(p,'PNG',optimize=True);files.append(str(p));components.append(s['component_id']);hashes.append(copy_hash(s))
 manifest={'format':'CAROUSEL','renderer_version':VERSION,'candidate_only':True,'production_binding':False,'expected_slides':len(slides),'rendered_slides':len(files),'outputs':files,'component_ids':components,'copy_sha256_by_slide':hashes,'asset_manifest_version':m['version']}
 (out/'render_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');return manifest
