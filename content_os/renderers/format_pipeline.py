from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw
from .carousel_renderer import RenderError, font, foil_text, paste_logo, cover_crop, draw_text_block, load_manifest

STORY=(1080,1920)
STATIC=(1080,1350)

def _bg(root:Path,size):
    return cover_crop(Image.open(root/'assets/background.jpg'),size).convert('RGBA')

def render_story(spec,root:Path,out_dir:Path):
    load_manifest(root)
    frames=spec.get('frames') or []
    if not 1 <= len(frames) <= 6: raise RenderError('STORY_FRAME_COUNT_INVALID')
    out_dir.mkdir(parents=True,exist_ok=True); outputs=[]
    for i,f in enumerate(frames,1):
        if len((f.get('headline') or '')+(f.get('body') or ''))>220: raise RenderError('COPY_DENSITY_CONFLICT')
        if f.get('hook') and f['hook'] != f['hook'].lower(): raise RenderError('GOLD_HOOK_NOT_LOWERCASE')
        base=_bg(root,STORY); draw=ImageDraw.Draw(base)
        if f.get('headline'): draw_text_block(draw,(540,520),f['headline'],font(root,'semibold',60),max_width=820,line_gap=10,anchor='ma')
        if f.get('hook'): foil_text(base,root,f['hook'],(540,900),145,880)
        if f.get('body'): draw_text_block(draw,(540,1160),f['body'],font(root,'regular',37),max_width=780,line_gap=13,anchor='ma')
        paste_logo(base,root,width=150,y=1770)
        p=out_dir/f'story_{i:02d}.png'; base.convert('RGB').save(p,'PNG',optimize=True); outputs.append(str(p))
    return {'format':'STORY','renderer_version':'1.0.0','expected_frames':len(frames),'rendered_frames':len(outputs),'outputs':outputs}

def render_static(spec,root:Path,out_dir:Path):
    load_manifest(root)
    if len((spec.get('headline') or '')+(spec.get('body') or ''))>250: raise RenderError('COPY_DENSITY_CONFLICT')
    if spec.get('hook') and spec['hook'] != spec['hook'].lower(): raise RenderError('GOLD_HOOK_NOT_LOWERCASE')
    out_dir.mkdir(parents=True,exist_ok=True); base=_bg(root,STATIC); draw=ImageDraw.Draw(base)
    if spec.get('headline'): draw_text_block(draw,(540,410),spec['headline'],font(root,'semibold',56),max_width=840,line_gap=9,anchor='ma')
    if spec.get('hook'): foil_text(base,root,spec['hook'],(540,700),135,860)
    if spec.get('body'): draw_text_block(draw,(540,895),spec['body'],font(root,'regular',33),max_width=780,line_gap=11,anchor='ma')
    paste_logo(base,root,width=150,y=1230); p=out_dir/'static_post.png'; base.convert('RGB').save(p,'PNG',optimize=True)
    return {'format':'STATIC_POST','renderer_version':'1.0.0','outputs':[str(p)]}

def build_reel_package(spec):
    hook=(spec.get('hook') or '').strip(); beats=spec.get('beats') or []
    if not hook: raise RenderError('REEL_HOOK_REQUIRED')
    if not 3 <= len(beats) <= 8: raise RenderError('REEL_BEAT_COUNT_INVALID')
    out=[]
    for i,b in enumerate(beats,1):
        if not b.get('voiceover') and not b.get('on_screen_text'): raise RenderError('REEL_BEAT_EMPTY')
        out.append({'beat':i,'duration_s':b.get('duration_s',3),'shot':b.get('shot','faceless editorial b-roll'),'voiceover':b.get('voiceover',''),'on_screen_text':b.get('on_screen_text','')})
    return {'format':'REEL','execution_state':'SCRIPT_SHOT_PACKAGE_READY','hook':hook,'beats':out,'cta':spec.get('cta',''),'video_rendered':False}
