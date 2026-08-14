import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
import unittest

ROOT=Path(__file__).parents[1]

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

sys.path.insert(0, str(ROOT.parent))
radar=load(ROOT/'ideas'/'radar.py','idea_radar')
NOW=datetime(2026,8,14,10,58,tzinfo=timezone.utc)

class IdeaRadarTests(unittest.TestCase):
    def base(self, **kw):
        d={
            'source_type':'RESEARCH_LIBRARY','source_ref':'RSH-X','title':'Alvás és esti éhség',
            'topic_domain':'RECOVERY','subtopic':'sleep','persona':'GENERAL','problem':'esti éhség',
            'proposed_angle':'mechanizmus','proposed_core_thesis':'a rövid alvás növelheti az energiabevitelt',
            'why_now':'new evidence','evidence_readiness':'REUSABLE_RESEARCH',
            'novelty_score':80,'practical_value_score':90,'brand_fit_score':95,'timeliness_score':75,
        }
        d.update(kw); return d

    def test_radar_never_auto_selects(self):
        idea=radar.triage_candidate(self.base(),idea_id='IDEA-20260814-001',now=NOW)
        self.assertEqual(idea.status,'READY_FOR_DECISION')
        self.assertEqual(idea.human_decision,'')

    def test_adjacent_scope(self):
        idea=radar.triage_candidate(self.base(),idea_id='IDEA-20260814-001',now=NOW)
        self.assertEqual(idea.scope_class,'ADJACENT')

    def test_out_of_scope_deferred(self):
        idea=radar.triage_candidate(self.base(topic_domain='CRYPTO'),idea_id='IDEA-20260814-001',now=NOW)
        self.assertEqual(idea.scope_class,'OUT_OF_SCOPE')
        self.assertEqual(idea.status,'DEFERRED')
        self.assertEqual(idea.priority_score,0.0)

    def test_tier3_routing(self):
        idea=radar.triage_candidate(self.base(title='Gyógyszer elhagyása fogyás miatt'),idea_id='IDEA-20260814-001',now=NOW)
        self.assertEqual(idea.health_risk_tier,'TIER_3')
        self.assertIn('TIER_3',idea.decision_reason)

    def test_semantic_duplicate(self):
        existing=[{'master_id':'MASTER-1','topic':'RECOVERY','problem':'esti éhség','core_thesis':'a rövid alvás növelheti az energiabevitelt','angle':'mechanizmus'}]
        idea=radar.triage_candidate(self.base(),idea_id='IDEA-20260814-001',now=NOW,existing_rows=existing)
        self.assertEqual(idea.duplicate_status,'DUPLICATE')
        self.assertEqual(idea.status,'DEFERRED')
        self.assertIn('MASTER-1',idea.similar_master_ids)

    def test_missing_thesis_needs_review(self):
        idea=radar.triage_candidate(self.base(proposed_core_thesis=''),idea_id='IDEA-20260814-001',now=NOW)
        self.assertEqual(idea.duplicate_status,'NEEDS_REVIEW')
        self.assertEqual(idea.status,'TRIAGED')

    def test_priority_bounded(self):
        idea=radar.triage_candidate(self.base(novelty_score=999,brand_fit_score=-10),idea_id='IDEA-20260814-001',now=NOW)
        self.assertTrue(0 <= idea.priority_score <= 100)
        self.assertEqual(idea.novelty_score,100.0)
        self.assertEqual(idea.brand_fit_score,0.0)

    def test_human_select_then_promote(self):
        idea=radar.triage_candidate(self.base(),idea_id='IDEA-20260814-001',now=NOW)
        selected=radar.apply_human_decision(idea,'SELECT')
        self.assertEqual(selected.status,'SELECTED')
        promoted=radar.promote_selected(selected,'MASTER-9')
        self.assertEqual(promoted.status,'PROMOTED')
        self.assertEqual(promoted.promoted_master_id,'MASTER-9')

    def test_promote_without_select_blocked(self):
        idea=radar.triage_candidate(self.base(),idea_id='IDEA-20260814-001',now=NOW)
        with self.assertRaises(PermissionError):
            radar.promote_selected(idea,'MASTER-9')

    def test_research_more_not_selected(self):
        idea=radar.triage_candidate(self.base(),idea_id='IDEA-20260814-001',now=NOW)
        updated=radar.apply_human_decision(idea,'RESEARCH_MORE')
        self.assertEqual(updated.status,'TRIAGED')
        with self.assertRaises(PermissionError):
            radar.promote_selected(updated,'MASTER-9')

    def test_id_generation(self):
        self.assertEqual(radar.next_idea_id(['IDEA-20260814-001','IDEA-20260814-007'],NOW),'IDEA-20260814-008')

    def test_row_schema_exact(self):
        idea=radar.triage_candidate(self.base(),idea_id='IDEA-20260814-001',now=NOW)
        self.assertEqual(len(idea.to_row()),len(radar.IDEA_INBOX_COLUMNS))
        self.assertEqual(radar.IDEA_INBOX_COLUMNS[-5:],['scope_class','proposed_core_thesis','priority_score','similar_master_ids','decision_reason'])

    def test_rank_candidates_detects_in_batch_overlap(self):
        out=radar.rank_candidates([self.base(title='A'),self.base(title='B')],now=NOW)
        self.assertEqual(len(out),2)
        self.assertIn('DUPLICATE',{x.duplicate_status for x in out})

if __name__=='__main__': unittest.main()
