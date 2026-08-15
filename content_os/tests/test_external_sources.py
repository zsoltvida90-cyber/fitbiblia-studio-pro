import unittest

from content_os.research.external_sources import normalize_external_source


class ExternalSourceTests(unittest.TestCase):
    def test_youtube_transcript_defaults_to_expert_context(self):
        p = normalize_external_source({
            'source_type': 'YOUTUBE_TRANSCRIPT',
            'source_ref': 'https://youtu.be/example',
            'title': 'Long-form researcher interview',
            'creator': 'Dr Example',
            'transcript_ref': 'https://example.com/transcript',
            'transcript_locator': '00:42:10-00:47:30',
        })
        self.assertEqual(p.knowledge_lane, 'EXPERT_CONTEXT')
        self.assertEqual(p.source_role, 'CONTEXT')
        self.assertFalse(p.factual_claim_upgrade_allowed)
        self.assertTrue(p.attribution_required)

    def test_preprint_is_primary_candidate_but_not_auto_approved(self):
        p = normalize_external_source({
            'source_type': 'PREPRINT',
            'source_ref': 'https://example.org/preprint/1',
            'title': 'New training model',
            'creator': 'Research Group',
            'review_state': 'PREPRINT',
        })
        self.assertEqual(p.knowledge_lane, 'SCIENCE_EVIDENCE')
        self.assertEqual(p.source_role, 'PRIMARY_CANDIDATE')
        self.assertEqual(p.review_state, 'PREPRINT')
        self.assertFalse(p.factual_claim_upgrade_allowed)
        self.assertIn('Non-peer-reviewed', p.notes)

    def test_author_reported_research_stays_labeled(self):
        p = normalize_external_source({
            'source_type': 'PERSONAL_RESEARCH_REPORT',
            'source_ref': 'https://researcher.example/report',
            'title': 'Own cohort observations',
            'creator': 'Researcher',
            'review_state': 'AUTHOR_REPORTED',
        })
        self.assertEqual(p.review_state, 'AUTHOR_REPORTED')
        self.assertFalse(p.factual_claim_upgrade_allowed)

    def test_external_source_cannot_impersonate_audience_signal(self):
        with self.assertRaisesRegex(ValueError, 'EXTERNAL_SOURCE_NOT_AUDIENCE_SIGNAL'):
            normalize_external_source({
                'source_type': 'PODCAST_TRANSCRIPT',
                'source_ref': 'https://example.com/episode',
                'title': 'Episode',
                'creator': 'Expert',
                'knowledge_lane': 'AUDIENCE_SIGNAL',
            })

    def test_provenance_fields_are_required(self):
        base = {'source_type': 'PODCAST_TRANSCRIPT', 'source_ref': 'x', 'title': 't', 'creator': 'c'}
        for field, code in [
            ('source_ref', 'EXTERNAL_SOURCE_REF_REQUIRED'),
            ('title', 'EXTERNAL_SOURCE_TITLE_REQUIRED'),
            ('creator', 'EXTERNAL_SOURCE_CREATOR_REQUIRED'),
        ]:
            item = dict(base)
            item[field] = ''
            with self.assertRaisesRegex(ValueError, code):
                normalize_external_source(item)


if __name__ == '__main__':
    unittest.main()
