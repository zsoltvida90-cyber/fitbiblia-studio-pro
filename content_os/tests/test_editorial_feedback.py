import unittest
from datetime import datetime,timezone
from content_os.feedback.editorial_feedback import *
NOW=datetime(2026,8,14,11,30,tzinfo=timezone.utc)

class FeedbackTests(unittest.TestCase):
    def rec(self,i,asset='A1',archive='',ftype='VISUAL',rule='use more negative space',outcome='ACCEPTED'):
        return create_feedback(feedback_id=f'FB-{i}',now=NOW,feedback_type=ftype,field_or_component='layout',before_summary='dense layout',after_summary='more negative space',reason='mobile hierarchy',outcome=outcome,confidence='HIGH',reusable_scope='VISUAL_RENDERER',candidate_rule=rule,asset_id=asset,accepted_archive_id=archive).__dict__

    def test_delta_required(self):
        with self.assertRaisesRegex(ValueError,'FEEDBACK_DELTA_REQUIRED'):
            create_feedback(feedback_id='F',now=NOW,feedback_type='VISUAL',field_or_component='x',before_summary='same',after_summary='same',reason='x',outcome='ACCEPTED')

    def test_reason_required(self):
        with self.assertRaisesRegex(ValueError,'FEEDBACK_REASON_REQUIRED'):
            create_feedback(feedback_id='F',now=NOW,feedback_type='VISUAL',field_or_component='x',before_summary='a',after_summary='b',reason='',outcome='ACCEPTED')

    def test_new_feedback_is_observation(self):
        r=self.rec(1); self.assertEqual(r['rule_status'],'OBSERVATION')

    def test_one_record_not_hypothesis(self):
        p=synthesize_patterns([self.rec(1)])[0]; self.assertEqual(p.status,'OBSERVATION')

    def test_repeated_across_assets_becomes_hypothesis(self):
        p=synthesize_patterns([self.rec(1,'A1'),self.rec(2,'A2'),self.rec(3,'A3')])[0]
        self.assertEqual(p.status,'HYPOTHESIS'); self.assertEqual(p.unique_assets,3)

    def test_same_asset_repetition_not_enough(self):
        p=synthesize_patterns([self.rec(1,'A1'),self.rec(2,'A1'),self.rec(3,'A1')])[0]; self.assertEqual(p.status,'OBSERVATION')

    def test_rejected_feedback_excluded(self):
        rows=[self.rec(1,'A1'),self.rec(2,'A2'),self.rec(3,'A3')]; rows[2]['rule_status']='REJECTED'
        p=synthesize_patterns(rows)[0]; self.assertEqual(p.status,'OBSERVATION')

    def test_two_archives_raise_confidence(self):
        p=synthesize_patterns([self.rec(1,'A1','AR1'),self.rec(2,'A2','AR2'),self.rec(3,'A3','AR3')])[0]; self.assertEqual(p.confidence,'HIGH')

    def test_science_pattern_never_auto_adopts(self):
        p=synthesize_patterns([self.rec(1,'A1','AR1','SCIENCE_WORDING','keep caveat'),self.rec(2,'A2','AR2','SCIENCE_WORDING','keep caveat'),self.rec(3,'A3','AR3','SCIENCE_WORDING','keep caveat')])[0]
        self.assertTrue(p.requires_science_review)
        with self.assertRaisesRegex(PermissionError,'SCIENCE_POLICY_REVIEW_REQUIRED'): adopt_pattern(p,human_approved=True,canonical_policy_ref='04_SCIENCE.md')

    def test_adoption_requires_human_and_policy_ref(self):
        p=synthesize_patterns([self.rec(1,'A1'),self.rec(2,'A2'),self.rec(3,'A3')])[0]
        with self.assertRaisesRegex(PermissionError,'HUMAN_POLICY_APPROVAL_REQUIRED'): adopt_pattern(p)
        with self.assertRaisesRegex(ValueError,'CANONICAL_POLICY_REF_REQUIRED'): adopt_pattern(p,human_approved=True)
        x=adopt_pattern(p,human_approved=True,canonical_policy_ref='06_VISUAL.md'); self.assertEqual(x['rule_status'],'ADOPTED')

    def test_id_generation(self):
        self.assertEqual(next_feedback_id(['FB-20260814-001','FB-20260814-009'],NOW),'FB-20260814-010')

    def test_row_schema(self):
        r=create_feedback(feedback_id='F',now=NOW,feedback_type='COPY',field_or_component='hook',before_summary='a',after_summary='b',reason='clearer',outcome='ACCEPTED')
        self.assertEqual(len(r.to_row()),21)

if __name__=='__main__':unittest.main()
