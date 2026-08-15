import unittest
from content_os.ideas import source_adapters as sa

class AdapterTests(unittest.TestCase):
    def editorial(self, **kw):
        d={'title':'Alvás és étvágy','topic_domain':'RECOVERY','problem':'esti éhség','proposed_angle':'mechanizmus','proposed_core_thesis':'a kevés alvás növelheti az energiabevitelt','why_now':'friss adat','novelty_score':80,'practical_value_score':90,'brand_fit_score':95,'timeliness_score':70}
        d.update(kw); return d

    def test_research_finding_becomes_reusable_not_approved(self):
        row={'finding_id':'F1','research_id':'R1','finding':'x','integrity_gate':'OK','freshness_gate':'FRESH','reusable':'YES','finding_type':'EVIDENCE','confidence':'HIGH'}
        p=sa.research_finding_packet(row,self.editorial())
        self.assertEqual(p.evidence_readiness,'REUSABLE_RESEARCH')
        self.assertEqual(p.source_ref,'research://R1/finding/F1')

    def test_research_finding_cannot_claim_registry_approval(self):
        row={'finding_id':'F1','research_id':'R1','finding':'x','integrity_gate':'OK','freshness_gate':'FRESH','reusable':'YES'}
        with self.assertRaises(ValueError):
            sa.research_finding_packet(row,self.editorial(evidence_readiness='KNOWN_APPROVED'))

    def test_research_adopted_refs_are_structured(self):
        row={'finding_id':'F1','research_id':'R1','finding':'x','integrity_gate':'OK','freshness_gate':'FRESH','reusable':'YES','adopted_in_refs':'MASTER-1;MASTER-2'}
        p=sa.research_finding_packet(row,self.editorial())
        self.assertEqual(p.known_master_refs,'MASTER-1;MASTER-2')

    def test_stale_research_needs_research(self):
        row={'finding_id':'F1','research_id':'R1','finding':'x','integrity_gate':'OK','freshness_gate':'STALE','reusable':'YES'}
        p=sa.research_finding_packet(row,self.editorial())
        self.assertEqual(p.evidence_readiness,'RESEARCH_NEEDED')

    def test_audience_signal_is_demand_not_science(self):
        row={'signal_id':'SIG-1','recurrence_state':'RECURRING','confidence':'MEDIUM'}
        p=sa.audience_signal_packet(row,self.editorial())
        self.assertEqual(p.source_type,'AUDIENCE_SIGNAL')
        self.assertEqual(p.evidence_readiness,'UNKNOWN')
        self.assertIn('not scientific truth',p.notes)

    def test_audience_signal_cannot_approve_claim(self):
        with self.assertRaises(ValueError):
            sa.audience_signal_packet({'signal_id':'SIG-1'},self.editorial(evidence_readiness='KNOWN_APPROVED'))

    def test_current_research_stays_unvalidated(self):
        p=sa.current_research_packet('web://paper-1',self.editorial(evidence_readiness='KNOWN_APPROVED'))
        self.assertEqual(p.evidence_readiness,'RESEARCH_NEEDED')

    def test_external_podcast_becomes_external_knowledge_not_approved(self):
        src={
            'source_type':'PODCAST_TRANSCRIPT',
            'source_ref':'https://example.com/podcast/1',
            'title':'Researcher interview',
            'creator':'Dr Example',
            'transcript_locator':'00:15:10-00:18:00',
            'primary_artifact_refs':'preprint://example-1',
            'review_state':'AUTHOR_REPORTED',
        }
        p=sa.external_source_packet(src,self.editorial())
        self.assertEqual(p.source_type,'EXTERNAL_KNOWLEDGE')
        self.assertEqual(p.evidence_readiness,'RESEARCH_NEEDED')
        self.assertIn('knowledge_lane=EXPERT_CONTEXT',p.notes)
        self.assertIn('primary_artifact_refs=preprint://example-1',p.notes)
        self.assertIn('transcript_locator=00:15:10-00:18:00',p.notes)

    def test_external_source_cannot_claim_registry_approval(self):
        src={'source_type':'YOUTUBE_TRANSCRIPT','source_ref':'https://youtu.be/x','title':'Talk','creator':'Researcher'}
        with self.assertRaisesRegex(ValueError,'EXTERNAL_SOURCE_NOT_CLAIM_AUTHORITY'):
            sa.external_source_packet(src,self.editorial(evidence_readiness='KNOWN_APPROVED'))

    def test_external_source_requires_creator_provenance(self):
        src={'source_type':'PODCAST_TRANSCRIPT','source_ref':'https://example.com/p','title':'Episode'}
        with self.assertRaisesRegex(ValueError,'EXTERNAL_SOURCE_CREATOR_REQUIRED'):
            sa.external_source_packet(src,self.editorial())

    def test_missing_editorial_synthesis_rejected(self):
        with self.assertRaisesRegex(ValueError,'CANDIDATE_SYNTHESIS_REQUIRED'):
            sa.manual_packet({'title':'x'})

    def test_manual_packet_has_provenance(self):
        p=sa.manual_packet(self.editorial())
        self.assertEqual(p.source_type,'MANUAL')
        self.assertTrue(p.source_ref)

    def test_scores_bounded(self):
        p=sa.manual_packet(self.editorial(novelty_score=500,brand_fit_score=-2))
        self.assertEqual(p.novelty_score,100.0)
        self.assertEqual(p.brand_fit_score,0.0)

    def test_editorial_gap_not_evidence_without_claims(self):
        p=sa.editorial_gap_packet('gap://training',self.editorial(evidence_readiness='KNOWN_APPROVED'))
        self.assertEqual(p.evidence_readiness,'UNKNOWN')

if __name__=='__main__': unittest.main()
