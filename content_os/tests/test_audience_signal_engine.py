import unittest
from datetime import datetime,timezone
from content_os.audience.signal_engine import *
NOW=datetime(2026,8,14,11,50,tzinfo=timezone.utc)

class AudienceSignalTests(unittest.TestCase):
    def sig(self,i,ref=None,problem='esti édességvágy',topic='NUTRITION'):
        s=create_signal(signal_id=f'SIG-{i}',now=NOW,source_type='COMMENT',source_ref=ref or f'comment-{i}',text_summary='Este mindig rám tör az édességvágy',normalized_problem=problem,topic_domain=topic,intent_type='PAIN',persona_candidate='KATA')
        return s.__dict__
    def test_privacy_redaction(self):
        s=create_signal(signal_id='S',now=NOW,source_type='DM',source_ref='zsolt@example.com',text_summary='Írj zsolt@example.com vagy +43 660 1234567 @username https://x.com',normalized_problem='kapcsolat',topic_domain='LIFE_SYSTEMS')
        self.assertNotIn('zsolt@example.com',s.text_summary);self.assertTrue(s.source_ref.startswith('anon:'));self.assertIn('[email]',s.text_summary);self.assertIn('[phone]',s.text_summary)
    def test_summary_length(self):self.assertLessEqual(len(sanitize_summary('x'*500)),280)
    def test_one_signal_one_off(self):self.assertEqual(cluster_signals([self.sig(1)])[0].state,'ONE_OFF')
    def test_three_signals_recurring(self):self.assertEqual(cluster_signals([self.sig(1),self.sig(2),self.sig(3)])[0].state,'RECURRING')
    def test_ten_five_sources_validated(self):
        rows=[self.sig(i,ref=f'c-{i%5}') for i in range(10)];self.assertEqual(cluster_signals(rows)[0].state,'VALIDATED_PATTERN')
    def test_ten_one_source_not_validated(self):
        rows=[self.sig(i,ref='same') for i in range(10)];self.assertEqual(cluster_signals(rows)[0].state,'RECURRING')
    def test_inactive_excluded(self):
        rows=[self.sig(1),self.sig(2),self.sig(3)];rows[2]['status']='REJECTED';self.assertEqual(cluster_signals(rows)[0].state,'ONE_OFF')
    def test_one_off_cannot_seed_idea(self):
        with self.assertRaisesRegex(PermissionError,'AUDIENCE_PATTERN_INSUFFICIENT'):idea_seed(cluster_signals([self.sig(1)])[0])
    def test_recurring_seed_not_science(self):
        c=cluster_signals([self.sig(1),self.sig(2),self.sig(3)])[0];x=idea_seed(c);self.assertEqual(x['evidence_readiness'],'UNKNOWN');self.assertEqual(x['source_type'],'AUDIENCE_SIGNAL')
    def test_cluster_mismatch(self):
        s=create_signal(signal_id='S',now=NOW,source_type='COMMENT',source_ref='1',text_summary='x',normalized_problem='p1',topic_domain='NUTRITION');c=cluster_signals([self.sig(1)])[0]
        with self.assertRaisesRegex(ValueError,'AUDIENCE_CLUSTER_MISMATCH'):apply_cluster_state(s,c)
    def test_invalid_source(self):
        with self.assertRaisesRegex(ValueError,'AUDIENCE_SOURCE_INVALID'):create_signal(signal_id='S',now=NOW,source_type='TRACKER',source_ref='1',text_summary='x',normalized_problem='p',topic_domain='NUTRITION')
    def test_id_generation(self):self.assertEqual(next_signal_id(['SIG-20260814-001','SIG-20260814-008'],NOW),'SIG-20260814-009')
    def test_schema(self):
        s=create_signal(signal_id='S',now=NOW,source_type='COMMENT',source_ref='1',text_summary='x',normalized_problem='p',topic_domain='NUTRITION');self.assertEqual(len(s.to_row()),15)
if __name__=='__main__':unittest.main()
