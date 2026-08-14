import unittest
from datetime import datetime, timezone
from content_os.queue.production_queue import *
NOW=datetime(2026,8,14,11,20,tzinfo=timezone.utc)
LATER=datetime(2026,8,14,11,21,tzinfo=timezone.utc)

class QueueTests(unittest.TestCase):
    def idea(self, **kw):
        d={'idea_id':'IDEA-1','human_decision':'SELECT','status':'SELECTED','title':'Teszt','persona':'GENERAL','health_risk_tier':'TIER_1','scope_class':'CORE','priority_score':88}
        d.update(kw); return d

    def q(self, **kw):
        return create_from_selected_idea(self.idea(**kw),queue_id='QUEUE-1',now=NOW,target_platform='INSTAGRAM',output_type='CAROUSEL',objective='SAVE')

    def test_selected_idea_creates_queue(self):
        q=self.q(); self.assertEqual(q.stage,'SELECTED'); self.assertEqual(q.publication_status,'PLANNED')

    def test_unselected_idea_blocked(self):
        with self.assertRaises(PermissionError): create_from_selected_idea(self.idea(human_decision=''),queue_id='Q',now=NOW)

    def test_direct_request_requires_selection_intent(self):
        with self.assertRaises(PermissionError): create_from_direct_request(queue_id='Q',now=NOW,title='x',target_platform='INSTAGRAM',output_type='CAROUSEL',objective='SAVE')
        q=create_from_direct_request(queue_id='Q',now=NOW,title='x',target_platform='INSTAGRAM',output_type='CAROUSEL',objective='SAVE',selection_intent=True)
        self.assertEqual(q.stage,'SELECTED')

    def test_out_of_scope_blocked(self):
        with self.assertRaisesRegex(PermissionError,'SCOPE_EXPANSION_REQUIRED'): self.q(scope_class='OUT_OF_SCOPE')

    def test_invalid_transition_blocked(self):
        with self.assertRaisesRegex(PermissionError,'QUEUE_TRANSITION_INVALID'): transition(self.q(),'PUBLISHED',now=LATER)

    def test_master_approved_needs_authority(self):
        q=transition(self.q(),'MASTER_DRAFT',now=LATER)
        q=transition(q,'MASTER_REVIEW',now=LATER)
        with self.assertRaisesRegex(PermissionError,'MASTER_AUTHORITY_REQUIRED'): transition(q,'MASTER_APPROVED',now=LATER,master_id='M1')
        q=transition(q,'MASTER_APPROVED',now=LATER,master_id='M1',authority=AuthorityState(master_approved=True))
        self.assertEqual(q.master_id,'M1')

    def test_tier3_master_needs_health_review(self):
        q=self.q(health_risk_tier='TIER_3'); q=transition(q,'MASTER_DRAFT',now=LATER); q=transition(q,'MASTER_REVIEW',now=LATER)
        with self.assertRaisesRegex(PermissionError,'HEALTH_RISK_REVIEW_REQUIRED'):
            transition(q,'MASTER_APPROVED',now=LATER,master_id='M1',authority=AuthorityState(master_approved=True))
        q=transition(q,'MASTER_APPROVED',now=LATER,master_id='M1',authority=AuthorityState(master_approved=True,health_review_ok=True))
        self.assertEqual(q.stage,'MASTER_APPROVED')

    def test_acceptance_requires_human_and_qa(self):
        q=self.q(); q=transition(q,'MASTER_DRAFT',now=LATER); q=transition(q,'MASTER_REVIEW',now=LATER); q=transition(q,'MASTER_APPROVED',now=LATER,master_id='M',authority=AuthorityState(master_approved=True)); q=transition(q,'PACKAGING',now=LATER); q=transition(q,'QA',now=LATER); q=transition(q,'HUMAN_REVIEW',now=LATER,qa_status='PASS')
        with self.assertRaisesRegex(PermissionError,'HUMAN_ACCEPTANCE_REQUIRED'): transition(q,'ACCEPTED',now=LATER)
        q=transition(q,'ACCEPTED',now=LATER,authority=AuthorityState(human_acceptance=True))
        self.assertEqual(q.publication_status,'PLANNED')

    def test_bad_qa_cannot_accept(self):
        q=self.q(); q=transition(q,'MASTER_DRAFT',now=LATER); q=transition(q,'MASTER_REVIEW',now=LATER); q=transition(q,'MASTER_APPROVED',now=LATER,master_id='M',authority=AuthorityState(master_approved=True)); q=transition(q,'PACKAGING',now=LATER); q=transition(q,'QA',now=LATER); q=transition(q,'HUMAN_REVIEW',now=LATER,qa_status='REVISE')
        with self.assertRaisesRegex(PermissionError,'QA_PASS_REQUIRED'): transition(q,'ACCEPTED',now=LATER,authority=AuthorityState(human_acceptance=True))

    def test_archive_needs_verified_authority(self):
        q=self.q(); q=transition(q,'MASTER_DRAFT',now=LATER); q=transition(q,'MASTER_REVIEW',now=LATER); q=transition(q,'MASTER_APPROVED',now=LATER,master_id='M',authority=AuthorityState(master_approved=True)); q=transition(q,'PACKAGING',now=LATER); q=transition(q,'QA',now=LATER); q=transition(q,'HUMAN_REVIEW',now=LATER,qa_status='PASS'); q=transition(q,'ACCEPTED',now=LATER,authority=AuthorityState(human_acceptance=True))
        with self.assertRaises(PermissionError): transition(q,'ARCHIVED',now=LATER,archive_id='A1')
        q=transition(q,'ARCHIVED',now=LATER,archive_id='A1',authority=AuthorityState(archive_verified=True))
        self.assertEqual(q.archive_id,'A1'); self.assertEqual(q.publication_status,'PLANNED')

    def test_publish_needs_distribution_authority(self):
        q=self._archived()
        with self.assertRaisesRegex(PermissionError,'DISTRIBUTION_AUTHORITY_REQUIRED'): transition(q,'PUBLISHED',now=LATER)
        q=transition(q,'PUBLISHED',now=LATER,authority=AuthorityState(distribution_published=True))
        self.assertEqual(q.publication_status,'PUBLISHED')

    def test_schedule_then_publish(self):
        q=self._archived(); q=transition(q,'SCHEDULED',now=LATER,authority=AuthorityState(distribution_scheduled=True)); self.assertEqual(q.publication_status,'SCHEDULED'); q=transition(q,'PUBLISHED',now=LATER,authority=AuthorityState(distribution_published=True)); self.assertEqual(q.stage,'PUBLISHED')

    def _archived(self):
        q=self.q(); q=transition(q,'MASTER_DRAFT',now=LATER); q=transition(q,'MASTER_REVIEW',now=LATER); q=transition(q,'MASTER_APPROVED',now=LATER,master_id='M',authority=AuthorityState(master_approved=True)); q=transition(q,'PACKAGING',now=LATER); q=transition(q,'QA',now=LATER); q=transition(q,'HUMAN_REVIEW',now=LATER,qa_status='PASS'); q=transition(q,'ACCEPTED',now=LATER,authority=AuthorityState(human_acceptance=True)); return transition(q,'ARCHIVED',now=LATER,archive_id='A',authority=AuthorityState(archive_verified=True))

    def test_id_generation(self):
        self.assertEqual(next_queue_id(['QUEUE-20260814-001','QUEUE-20260814-004'],NOW),'QUEUE-20260814-005')

    def test_row_schema(self):
        self.assertEqual(len(self.q().to_row()),25); self.assertEqual(QUEUE_COLUMNS[-1],'scope_class')

if __name__=='__main__': unittest.main()
