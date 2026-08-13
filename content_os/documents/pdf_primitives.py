from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
class PdfBuildError(RuntimeError):pass
def register_fonts(root):
 root=Path(root)
 try:
  pdfmetrics.registerFont(TTFont('FitBody',str(root/'assets/instrument_sans/static/InstrumentSans-Regular.ttf')))
  pdfmetrics.registerFont(TTFont('FitBodySemi',str(root/'assets/instrument_sans/static/InstrumentSans-SemiBold.ttf')))
  pdfmetrics.registerFont(TTFont('FitHook',str(root/'assets/Fraunces-Italic.ttf')))
 except Exception as e:raise PdfBuildError(f'PDF_FONT_ERROR:{e}')
def wrap_lines(c,text,font,size,max_width):
 lines=[];cur=''
 for word in str(text or '').split():
  if c.stringWidth(word,font,size)>max_width:raise PdfBuildError('PDF_COPY_DENSITY_CONFLICT')
  trial=word if not cur else cur+' '+word
  if c.stringWidth(trial,font,size)<=max_width:cur=trial
  else:lines.append(cur);cur=word
 if cur:lines.append(cur)
 return lines
