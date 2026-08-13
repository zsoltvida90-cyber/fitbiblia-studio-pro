from __future__ import annotations
import argparse
import json
import tempfile
from pathlib import Path
from PIL import Image

from content_os.renderers.carousel_renderer import RenderError, render_carousel, load_manifest
from content_os.renderers.format_pipeline import render_story, render_static, build_reel_package
from content_os.semantic.dedup import compare
from content_os.learning.learning_engine import classify, assert_no_science_mutation
from content_os.integrations.meta_adapter import normalize_insights_response, normalize_webhook, upsert_decision

class Suite:
    def __init__(self): self.rows=[]
    def check(self,name,condition,detail=''):
        ok=bool(condition); self.rows.append({'name':name,'pass':ok,'detail':detail})
        if not ok: raise AssertionError(f'{name}: {detail}')
    def expect_error(self,name,fn,token):
        try: fn()
        except Exception as exc:
            self.check(name, token in str(exc), str(exc)); return
        self.check(name,False,'no exception')


def run(runtime_root: Path):
    s=Suite(); root=runtime_root.resolve()
    manifest=load_manifest(root)
    s.check('manifest_version', bool(manifest.get('version')), manifest.get('version',''))

    with tempfile.TemporaryDirectory(prefix='fitbiblia-e2e-') as td:
        td=Path(td)
        job={'slides':[
            {'slide_number':1,'role':'COVER','headline':'A kreatin időzítése','hook':'nem percre dől el','body':'A rendszeresség fontosabb.'},
            {'slide_number':2,'role':'INNER_EXPLAIN','headline':'A lényeg','body':'A napi rendszer fontosabb, mint a tökéletesnek hitt perc.'},
            {'slide_number':3,'role':'CTA','headline':'Tartsd egyszerűen','body':'Mentsd el későbbre.'},
        ]}
        result=render_carousel(job,root,td/'carousel')
        s.check('carousel_count',result['expected_slides']==result['rendered_slides']==3)
        s.check('carousel_manifest',(td/'carousel'/'render_manifest.json').exists())
        for p in result['outputs']:
            s.check('carousel_dimensions_'+Path(p).name,Image.open(p).size==(1080,1350))

        bad_order={'slides':[dict(job['slides'][0]),dict(job['slides'][1])]}; bad_order['slides'][1]['slide_number']=3
        s.expect_error('carousel_series_incomplete',lambda:render_carousel(bad_order,root,td/'badorder'),'SERIES_INCOMPLETE')
        dense={'slides':[{'slide_number':1,'role':'COVER','headline':'x'*150}]}
        s.expect_error('carousel_density',lambda:render_carousel(dense,root,td/'dense'),'COPY_DENSITY_CONFLICT')
        upper={'slides':[{'slide_number':1,'role':'COVER','headline':'Teszt','hook':'NEM JÓ'}]}
        s.expect_error('gold_hook_lowercase',lambda:render_carousel(upper,root,td/'upper'),'GOLD_HOOK_NOT_LOWERCASE')

        story=render_story({'frames':[{'headline':'Nem a kedved dönt','hook':'a rendszer','body':'A rossz napokra is építs.'}]},root,td/'story')
        s.check('story_count',story['rendered_frames']==1)
        s.check('story_dimensions',Image.open(story['outputs'][0]).size==(1080,1920))
        s.expect_error('story_zero',lambda:render_story({'frames':[]},root,td/'story0'),'STORY_FRAME_COUNT_INVALID')
        s.expect_error('story_seven',lambda:render_story({'frames':[{'headline':'x'}]*7},root,td/'story7'),'STORY_FRAME_COUNT_INVALID')

        static=render_static({'headline':'A hét nem hétfőn','hook':'kedden dől el','body':'A rendszer a rossz napot is túléli.'},root,td/'static')
        s.check('static_dimensions',Image.open(static['outputs'][0]).size==(1080,1350))

    reel=build_reel_package({'hook':'Mi számít igazán?','beats':[{'voiceover':'egy'},{'voiceover':'kettő'},{'on_screen_text':'három'}],'cta':'Mentsd el.'})
    s.check('reel_state',reel['execution_state']=='SCRIPT_SHOT_PACKAGE_READY')
    s.check('reel_not_video',reel['video_rendered'] is False)
    s.expect_error('reel_bad_count',lambda:build_reel_package({'hook':'x','beats':[{'voiceover':'a'}]}),'REEL_BEAT_COUNT_INVALID')

    exact={'topic':'kreatin','problem':'edzés előtt vagy után','core_thesis':'a rendszeres kreatin bevitel fontosabb mint a pontos időzítés','angle':'időzítés'}
    s.check('semantic_exact',compare(exact,exact).status=='DUPLICATE')
    hu={'topic':'fogyás','problem':'esti farkaséhség','core_thesis':'az esti éhség lehet a napközbeni alacsony telítettség következménye','angle':'való élet'}
    para={'topic':'fat loss','problem':'esti éhség','core_thesis':'az esti éhség lehet a napközbeni alacsony telítettség következménye','angle':'real life'}
    s.check('semantic_hu_paraphrase',compare(hu,para).status!='NEW',compare(hu,para).status)
    en={'topic':'creatine','problem':'before training or after training','core_thesis':'consistent creatine use matters more than exact timing','angle':'timing'}
    s.check('semantic_bilingual_neighbor',compare(exact,en).status!='NEW',compare(exact,en).status)

    s.expect_error('meta_raw_ref',lambda:normalize_insights_response({'data':[]},'asset'),'RAW_REF_REQUIRED')
    insight=normalize_insights_response({'data':[{'name':'saved','values':[{'value':50}]}]},'asset',raw_ingest_ref='raw://1')
    s.check('meta_missing_reach_unknown','reach' not in insight)
    event={'event_id':'evt-1','field':'insights','object':'instagram','time':'2026-08-13T19:00:00+02:00'}
    s.check('meta_first_append',upsert_decision([],event)['action']=='APPEND')
    s.check('meta_retry_ignore',upsert_decision(['evt-1'],event)['action']=='IGNORE_DUPLICATE')
    s.expect_error('meta_secret_block',lambda:normalize_webhook({'access_token':'secret'},'fitbiblia_ig','raw://x'),'SECRET_IN_PAYLOAD')

    s.check('learn_8',classify(8,'OK').confidence_state=='INSUFFICIENT_DATA')
    s.check('learn_15',classify(15,'OK').confidence_state=='EARLY_SIGNAL')
    s.check('learn_20',classify(20,'OK','mechanism hook hypothesis',['asset']).confidence_state=='HYPOTHESIS_READY')
    s.check('learn_bad_distribution',classify(30,'BLOCK','x',['asset']).confidence_state=='REJECTED')
    s.check('learn_missing_hypothesis',classify(20,'OK','',['asset']).confidence_state=='INTEGRITY_FAIL')
    s.expect_error('science_mutation_block',lambda:assert_no_science_mutation('claim_status'),'SCIENCE_MUTATION_FORBIDDEN')

    passed=sum(1 for r in s.rows if r['pass'])
    return {'passed':passed,'total':len(s.rows),'failed':len(s.rows)-passed,'results':s.rows}

if __name__=='__main__':
    p=argparse.ArgumentParser(description='Fit Biblia executable E2E stress harness')
    p.add_argument('--runtime-root',required=True,help='Directory containing asset_manifest.json and assets/ with verified canonical binaries')
    p.add_argument('--report',help='Optional JSON report path')
    args=p.parse_args(); report=run(Path(args.runtime_root))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if args.report: Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if report['failed']==0 else 1)
