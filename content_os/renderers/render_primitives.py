import hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
BONE='#EEE5CF'; CANVAS=(1080,1350)
class RenderError(RuntimeError):pass
def sha256(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
def load_manifest(root):
 m=json.loads((Path(root)/'asset_manifest.json').read_text(encoding='utf-8'))
 for k,s in m['assets'].items():
  p=Path(root)/'assets'/s['relative_path']
  if not p.exists():raise RenderError(f'ASSET_REQUIRED:{k}')
  if sha256(p)!=s['sha256']:raise RenderError(f'ASSET_HASH_MISMATCH:{k}')
 return m
def cover_crop(img,size=CANVAS):return ImageOps.fit(img.convert('RGB'),size,method=Image.Resampling.LANCZOS,centering=(.5,.5))
def font(root,which,size):
 rel={'regular':'instrument_sans/static/InstrumentSans-Regular.ttf','semibold':'instrument_sans/static/InstrumentSans-SemiBold.ttf','hook':'Fraunces-Italic.ttf'}[which]
 return ImageFont.truetype(str(Path(root)/'assets'/rel),size=size)
def wrap(draw,text,fnt,max_width):
 out=[]
 for para in str(text).split('\n'):
  if not para:out.append('');continue
  cur=''
  for word in para.split():
   if draw.textbbox((0,0),word,font=fnt)[2]>max_width:raise RenderError('COPY_DENSITY_CONFLICT')
   t=word if not cur else cur+' '+word
   if draw.textbbox((0,0),t,font=fnt)[2]<=max_width:cur=t
   else:out.append(cur);cur=word
  if cur:out.append(cur)
 return out
def draw_text_block(draw,xy,text,fnt,fill=BONE,max_width=888,line_gap=12,anchor='la'):
 y=xy[1];lines=wrap(draw,text,fnt,max_width)
 for line in lines:
  if not line:y+=max(1,int(fnt.size*.7))+line_gap;continue
  draw.text((xy[0],y),line,font=fnt,fill=fill,anchor=anchor);b=draw.textbbox((xy[0],y),line,font=fnt,anchor=anchor);y+=b[3]-b[1]+line_gap
 return y,lines
def foil_text(base,root,text,center,font_size,max_width=900):
 if text!=text.lower():raise RenderError('GOLD_HOOK_NOT_LOWERCASE')
 f=font(root,'hook',font_size);d=ImageDraw.Draw(Image.new('L',(1,1)));b=d.textbbox((0,0),text,font=f);mask=Image.new('L',(b[2]-b[0]+20,b[3]-b[1]+20),0);ImageDraw.Draw(mask).text((10-b[0],10-b[1]),text,font=f,fill=255);mask=mask.resize((int(mask.width*1.23),mask.height),Image.Resampling.LANCZOS)
 if mask.width>max_width:
  s=max_width/mask.width;mask=mask.resize((max_width,max(1,int(mask.height*s))),Image.Resampling.LANCZOS)
 foil=ImageOps.fit(Image.open(Path(root)/'assets/gold_foil.jpg').convert('RGB'),mask.size,method=Image.Resampling.LANCZOS);base.paste(foil,(int(center[0]-mask.width/2),int(center[1]-mask.height/2)),mask)
def paste_logo(base,root,width=150,y=1230):
 logo=Image.open(Path(root)/'assets/logo.png').convert('RGBA');logo=logo.crop(logo.getbbox());r=width/logo.width;logo=logo.resize((width,int(logo.height*r)),Image.Resampling.LANCZOS);base.alpha_composite(logo,((base.width-width)//2,y-logo.height//2))
def chevron(draw,x=1025,y=675,size=28,width=6):draw.line([(x-size//2,y-size),(x+size//2,y),(x-size//2,y+size)],fill=BONE,width=width,joint='curve')
