import json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor
from .pdf_primitives import PdfBuildError,register_fonts,wrap_lines
BONE=HexColor('#EEE5CF');GOLD=HexColor('#C9A227');DARK=HexColor('#06060A')
def build_short_pdf(spec,root,out_path):
 pages=spec.get('pages')or[]
 if not 2<=len(pages)<=8:raise PdfBuildError('SHORT_PDF_PAGE_COUNT_INVALID')
 root=Path(root);out_path=Path(out_path);register_fonts(root);out_path.parent.mkdir(parents=True,exist_ok=True);c=canvas.Canvas(str(out_path),pagesize=A4,pageCompression=1);W,H=A4;bg=ImageReader(str(root/'assets/background.jpg'));logo=root/'assets/logo.png'
 for idx,page in enumerate(pages,1):
  title=str(page.get('title')or'').strip();body=str(page.get('body')or'').strip();kicker=str(page.get('kicker')or'').strip()
  if not title:raise PdfBuildError('PDF_TITLE_REQUIRED')
  if len(title)+len(body)>1400:raise PdfBuildError('PDF_COPY_DENSITY_CONFLICT')
  c.setFillColor(DARK);c.rect(0,0,W,H,fill=1,stroke=0);c.drawImage(bg,0,0,width=W,height=H,mask='auto',preserveAspectRatio=False)
  if kicker:c.setFont('FitHook',24);c.setFillColor(GOLD);c.drawCentredString(W/2,H-135,kicker.lower())
  size=28 if idx==1 else 22;c.setFillColor(BONE);c.setFont('FitBodySemi',size);y=H-210
  for line in wrap_lines(c,title,'FitBodySemi',size,W-100):c.drawCentredString(W/2,y,line);y-=36
  c.setStrokeColor(GOLD);c.line(85,y-8,W-85,y-8);y-=55;c.setFont('FitBody',13.5);c.setFillColor(BONE);lines=wrap_lines(c,body,'FitBody',13.5,W-120)
  if len(lines)>24:raise PdfBuildError('PDF_COPY_DENSITY_CONFLICT')
  for line in lines:c.drawString(60,y,line);y-=21
  if idx>1 and logo.exists():c.drawImage(str(logo),W/2-42,35,width=84,height=28,mask='auto',preserveAspectRatio=True,anchor='c')
  c.setFont('FitBody',8);c.drawRightString(W-40,28,str(idx));c.showPage()
 c.save();result={'format':'SHORT_PDF','renderer_version':'1.0.0','expected_pages':len(pages),'rendered_pages':len(pages),'output':str(out_path),'human_visual_approval_required':True};out_path.with_suffix('.manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');return result
