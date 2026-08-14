from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from PIL import Image,ImageDraw,ImageEnhance
from .render_primitives import *
from .component_registry import validate_assignment

VERSION='3.1.0-candidate'
GOLD='#C7A14A'
MUTED='#BDB49F'


def copy_hash(s):
    raw='\n'.join([str(s.get('headline') or ''),str(s.get('hook') or ''),str(s.get('body') or '')])
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def base_canvas(root,veil=54):
    with Image.open(Path(root)/'assets/background.jpg') as im:
        base=cover_crop(im).convert('RGBA')
    base=ImageEnhance.Contrast(base).enhance(1.08)
    return Image.alpha_composite(base,Image.new('RGBA',base.size,(0,0,0,veil)))


def footer(base,root,is_last):
    d=ImageDraw.Draw(base)
    paste_logo(base,root,width=108,y=1262)
    if not is_last:
        chevron(d,x=1028,y=675,size=24,width=4)


def split_source(body):
    if '\n\nForrás:' in body:
        main,src=body.rsplit('\n\nForrás:',1)
        return main.strip(),'Forrás: '+src.strip()
    return body.strip(),''


def gold_rule(d,x1,y,x2,w=3):
    d.line((x1,y,x2,y),fill=GOLD,width=w)


def render_cover(s,root,is_last):
    base=base_canvas(root,48);d=ImageDraw.Draw(base)
    draw_text_block(d,(112,205),s.get('headline',''),font(root,'semibold',77),max_width=820,line_gap=2,anchor='la')
    gold_rule(d,112,445,280,3)
    foil_text(base,root,s.get('hook',''),(545,655),166,900)
    draw_text_block(d,(112,865),s.get('body',''),font(root,'regular',37),max_width=760,line_gap=7,anchor='la')
    if not is_last:
        chevron(d,x=1028,y=675,size=24,width=4)
    return base


def render_inner(s,root,is_last):
    base=base_canvas(root,60);d=ImageDraw.Draw(base)
    gold_rule(d,112,215,228,3)
    draw_text_block(d,(112,270),s.get('headline',''),font(root,'semibold',58),max_width=810,line_gap=5,anchor='la')
    y,_=draw_text_block(d,(112,575),s.get('body',''),font(root,'regular',37),max_width=810,line_gap=14,anchor='la')
    if y>1070:
        raise RenderError('COPY_DENSITY_CONFLICT')
    footer(base,root,is_last)
    return base


def draw_stat_parts(base,root,stat,xy,align='left'):
    d=ImageDraw.Draw(base)
    m=re.match(r'^([+\-]?\d+(?:[,.]\d+)?)\s*(.*)$',stat.strip())
    if not m:
        foil_text(base,root,stat.lower(),xy,124,470)
        return
    num,unit=m.group(1),m.group(2)
    if align=='left':
        foil_text(base,root,num.lower(),(xy[0]+150,xy[1]),150,360)
        if unit:
            d.text((xy[0],xy[1]+92),unit,font=font(root,'semibold',31),fill=BONE,anchor='la')
    else:
        foil_text(base,root,num.lower(),(xy[0]-135,xy[1]),150,340)
        if unit:
            d.text((xy[0],xy[1]+92),unit,font=font(root,'semibold',31),fill=BONE,anchor='ra')


def render_evidence(s,root,is_last):
    base=base_canvas(root,62);d=ImageDraw.Draw(base)
    stat=str(s.get('stat') or '').strip()
    main,src=split_source(str(s.get('body') or ''))
    n=int(s.get('slide_number') or 0)
    if n==3:
        if stat:
            draw_stat_parts(base,root,stat,(112,255),'left')
        gold_rule(d,112,440,300,3)
        draw_text_block(d,(112,485),s.get('headline',''),font(root,'semibold',53),max_width=800,line_gap=5,anchor='la')
        y,_=draw_text_block(d,(112,690),main,font(root,'regular',34),max_width=810,line_gap=12,anchor='la')
    elif n==4:
        draw_text_block(d,(112,245),s.get('headline',''),font(root,'semibold',53),max_width=700,line_gap=5,anchor='la')
        if stat:
            draw_stat_parts(base,root,stat,(955,470),'right')
        gold_rule(d,690,610,955,3)
        y,_=draw_text_block(d,(112,665),main,font(root,'regular',34),max_width=810,line_gap=12,anchor='la')
    else:
        if stat:
            foil_text(base,root,stat.lower(),(540,315),170,650)
        draw_text_block(d,(112,500),s.get('headline',''),font(root,'semibold',52),max_width=820,line_gap=5,anchor='la')
        gold_rule(d,112,650,260,3)
        y,_=draw_text_block(d,(112,700),main,font(root,'regular',33),max_width=810,line_gap=11,anchor='la')
    if y>1050:
        raise RenderError('COPY_DENSITY_CONFLICT')
    if src:
        draw_text_block(d,(112,1080),src,font(root,'regular',24),fill=MUTED,max_width=780,line_gap=5,anchor='la')
    footer(base,root,is_last)
    return base


def render_whisper(s,root,is_last):
    base=base_canvas(root,66);d=ImageDraw.Draw(base)
    draw_text_block(d,(112,250),s.get('headline',''),font(root,'semibold',54),max_width=810,line_gap=5,anchor='la')
    foil_text(base,root,s.get('hook',''),(540,625),108,790)
    gold_rule(d,395,730,685,2)
    y,_=draw_text_block(d,(112,815),s.get('body',''),font(root,'regular',34),max_width=760,line_gap=12,anchor='la')
    if y>1090:
        raise RenderError('COPY_DENSITY_CONFLICT')
    footer(base,root,is_last)
    return base


def render_protocol(s,root,is_last):
    base=base_canvas(root,60);d=ImageDraw.Draw(base)
    draw_text_block(d,(112,210),s.get('headline',''),font(root,'semibold',55),max_width=820,line_gap=5,anchor='la')
    blocks=[b.strip() for b in str(s.get('body') or '').split('\n\n') if b.strip()]
    y=505
    for idx,b in enumerate(blocks):
        m=re.match(r'^(\d{2})\s+(.*)$',b,re.S)
        num=m.group(1) if m else f'{idx+1:02d}'
        txt=m.group(2) if m else b
        d.text((112,y),num,font=font(root,'semibold',50),fill=BONE,anchor='la')
        gold_rule(d,112,y+66,188,2)
        end,_=draw_text_block(d,(235,y+2),txt,font(root,'regular',34),max_width=700,line_gap=10,anchor='la')
        y=max(y+150,end+42)
    if y>1140:
        raise RenderError('COPY_DENSITY_CONFLICT')
    footer(base,root,is_last)
    return base


def render_cta(s,root,is_last):
    base=base_canvas(root,70);d=ImageDraw.Draw(base)
    draw_text_block(d,(540,350),s.get('headline',''),font(root,'semibold',64),max_width=840,line_gap=5,anchor='ma')
    gold_rule(d,405,605,675,3)
    draw_text_block(d,(540,700),s.get('body',''),font(root,'regular',35),max_width=760,line_gap=12,anchor='ma')
    paste_logo(base,root,width=122,y=1135)
    return base


RENDERERS={
    'COVER_BIG_HOOK':render_cover,
    'INNER_EXPLAIN':render_inner,
    'NUMBER_EVIDENCE':render_evidence,
    'QUOTE_WHISPER':render_whisper,
    'THREE_STEP_PROTOCOL':render_protocol,
    'CTA_FOLLOW':render_cta,
}


def render_slide(s,root,is_last=False):
    cid=str(s.get('component_id') or '').strip().upper()
    validate_assignment(cid,s,allow_experimental=True)
    if cid not in RENDERERS:
        raise RenderError('COMPONENT_NOT_IMPLEMENTED')
    return RENDERERS[cid](s,root,is_last).convert('RGB')


def render_carousel(job,root,out_dir):
    m=load_manifest(root)
    slides=job.get('slides') or []
    if not slides:
        raise RenderError('SERIES_INCOMPLETE')
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    files=[];components=[];hashes=[]
    for i,s in enumerate(slides,1):
        if s.get('slide_number',i)!=i:
            raise RenderError('SERIES_INCOMPLETE')
        p=out/f'slide_{i:02d}.png'
        render_slide(s,root,i==len(slides)).save(p,'PNG',optimize=True)
        files.append(str(p));components.append(s['component_id']);hashes.append(copy_hash(s))
    manifest={
        'format':'CAROUSEL','renderer_version':VERSION,
        'candidate_only':True,'production_binding':False,
        'expected_slides':len(slides),'rendered_slides':len(files),
        'outputs':files,'component_ids':components,
        'copy_sha256_by_slide':hashes,'asset_manifest_version':m['version'],
    }
    (out/'render_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest
