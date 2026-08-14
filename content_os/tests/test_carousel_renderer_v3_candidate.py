import hashlib
import unittest
from content_os.renderers.carousel_renderer_v3_candidate import copy_hash,split_source,VERSION
from content_os.renderers.component_registry import validate_assignment

class CarouselV3CandidateTests(unittest.TestCase):
    def test_version_is_candidate(self): self.assertIn('candidate',VERSION)
    def test_copy_hash_is_stable(self):
        s={'headline':'h','hook':'k','body':'b'}
        self.assertEqual(copy_hash(s),hashlib.sha256('h\nk\nb'.encode()).hexdigest())
    def test_component_assignment_requires_matching_role(self):
        self.assertEqual(validate_assignment('COVER_BIG_HOOK',{'role':'COVER','headline':'x'},allow_experimental=True).component_id,'COVER_BIG_HOOK')
        with self.assertRaises(ValueError):validate_assignment('COVER_BIG_HOOK',{'role':'EVIDENCE','headline':'x'},allow_experimental=True)
    def test_source_split_preserves_space(self):
        main,src=split_source('body\n\nForrás: Journal, 2026');self.assertEqual(main,'body');self.assertEqual(src,'Forrás: Journal, 2026')
    def test_required_sleep_component_roles(self):
        pairs=[('COVER_BIG_HOOK','COVER'),('INNER_EXPLAIN','INNER_EXPLAIN'),('NUMBER_EVIDENCE','EVIDENCE'),('QUOTE_WHISPER','INSIGHT_WHISPER'),('THREE_STEP_PROTOCOL','LIST_PROTOCOL'),('CTA_FOLLOW','CTA')]
        for cid,role in pairs:validate_assignment(cid,{'role':role,'headline':'x','body':''},allow_experimental=True)
    def test_experimental_is_explicit(self):
        with self.assertRaises(PermissionError):validate_assignment('COVER_BIG_HOOK',{'role':'COVER','headline':'x'})
if __name__=='__main__':unittest.main()
