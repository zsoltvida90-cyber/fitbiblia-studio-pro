import argparse,tempfile
from pathlib import Path
from content_os.platforms.platform_contract import build_x_post,build_x_thread,validate_platform_output
from content_os.renderers.format_pipeline import build_reel_package
from content_os.documents.short_pdf import build_short_pdf

def run(root):
 assert build_x_post('a'*280)['character_count']==280
 assert len(build_x_thread(['egy','kettő'])['posts'])==2
 assert validate_platform_output('tiktok','REEL')['compatible']
 assert not validate_platform_output('x','CAROUSEL')['compatible']
 reel=build_reel_package({'target_platform':'TIKTOK','hook':'teszt','beats':[{'voiceover':'1'},{'voiceover':'2'},{'voiceover':'3'}]});assert reel['target_platform']=='TIKTOK' and reel['video_rendered'] is False
 pages=[{'title':'Első','kicker':'teszt','body':'Rövid tartalom.'},{'title':'Második','body':'Második oldal.'}]
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'test.pdf';result=build_short_pdf({'pages':pages},Path(root),p);assert p.exists() and p.with_suffix('.manifest.json').exists() and result['rendered_pages']==2 and result['human_visual_approval_required'] is True
 return 7
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--runtime-root',required=True);a=ap.parse_args();print(f'PASS {run(a.runtime_root)}/7')
