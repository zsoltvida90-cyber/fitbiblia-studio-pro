import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from PIL import Image
from content_os.renderers.component_registry import *
from content_os.visual.golden_regression import *
NOW=datetime(2026,8,14,11,40,tzinfo=timezone.utc)

class ComponentGoldenTests(unittest.TestCase):
    def test_experimental_component_not_production_active(self):
        with self.assertRaisesRegex(PermissionError,'COMPONENT_NOT_ACTIVE'): get_component('COVER_BIG_HOOK')
        self.assertEqual(get_component('COVER_BIG_HOOK',allow_experimental=True).status,'EXPERIMENTAL')

    def test_component_role_mismatch(self):
        with self.assertRaisesRegex(ValueError,'COMPONENT_ROLE_MISMATCH'):
            validate_assignment('COVER_BIG_HOOK',{'role':'EVIDENCE','headline':'x'},allow_experimental=True)

    def test_density_guard(self):
        with self.assertRaisesRegex(ValueError,'COPY_DENSITY_CONFLICT'):
            validate_assignment('COVER_BIG_HOOK',{'role':'COVER','headline':'x'*100},allow_experimental=True)

    def test_no_foil_component_rejects_hook(self):
        with self.assertRaisesRegex(ValueError,'COMPONENT_FOIL_NOT_ALLOWED'):
            validate_assignment('THREE_STEP_PROTOCOL',{'role':'LIST_PROTOCOL','headline':'x','body':'y','hook':'gold'},allow_experimental=True)

    def test_component_activation_requires_human(self):
        with self.assertRaisesRegex(PermissionError,'HUMAN_VISUAL_APPROVAL_REQUIRED'): activate_component('COVER_BIG_HOOK')
        self.assertEqual(activate_component('COVER_BIG_HOOK',human_approved=True).status,'ACTIVE')

    def test_golden_candidate_requires_human_nomination(self):
        args=dict(golden_id='G1',now=NOW,archive_id='AR1',asset_id='A1',master_id='M1',platform='INSTAGRAM',output_type='CAROUSEL',role_or_series='SERIES',quality_reason='strong',baseline_renderer_version='1',baseline_manifest_ref='manifest://1')
        with self.assertRaisesRegex(PermissionError,'HUMAN_GOLDEN_NOMINATION_REQUIRED'): create_golden_candidate(**args)
        g=create_golden_candidate(**args,human_nominated=True); self.assertEqual(g.status,'CANDIDATE')

    def test_golden_activation_requires_verified_archive_and_human(self):
        g=self.golden()
        with self.assertRaisesRegex(PermissionError,'HUMAN_GOLDEN_APPROVAL_REQUIRED'): activate_golden(g)
        with self.assertRaisesRegex(PermissionError,'GOLDEN_ARCHIVE_VERIFY_REQUIRED'): activate_golden(g,human_approved=True)
        self.assertEqual(activate_golden(g,human_approved=True,archive_verified=True).status,'ACTIVE')

    def test_exact_regression_pass(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/'a.png'; b=Path(td)/'b.png'; Image.new('RGB',(1080,1350),(1,2,3)).save(a); Image.new('RGB',(1080,1350),(1,2,3)).save(b)
            r=compare_series([a],[b],expected_size=(1080,1350)); self.assertEqual(r.status,'PASS_EXACT'); self.assertFalse(r.human_review_required)

    def test_changed_pixels_require_human_when_undeclared(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/'a.png'; b=Path(td)/'b.png'; Image.new('RGB',(1080,1350),(0,0,0)).save(a); Image.new('RGB',(1080,1350),(10,10,10)).save(b)
            r=compare_series([a],[b],expected_size=(1080,1350)); self.assertEqual(r.status,'HUMAN_REVIEW'); self.assertTrue(r.human_review_required)

    def test_declared_change_still_requires_human(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/'a.png'; b=Path(td)/'b.png'; Image.new('RGB',(1080,1350),(0,0,0)).save(a); Image.new('RGB',(1080,1350),(10,10,10)).save(b)
            r=compare_series([a],[b],expected_size=(1080,1350),intended_visual_change=True); self.assertEqual(r.status,'HUMAN_REVIEW')
            r=compare_series([a],[b],expected_size=(1080,1350),intended_visual_change=True,human_visual_approved=True); self.assertEqual(r.status,'PASS_APPROVED_CHANGE')

    def test_copy_or_asset_change_hard_fails(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/'a.png'; Image.new('RGB',(1080,1350),(0,0,0)).save(a)
            self.assertEqual(compare_series([a],[a],expected_size=(1080,1350),copy_fingerprint_equal=False).status,'VISUAL_REGRESSION_FAIL')
            self.assertEqual(compare_series([a],[a],expected_size=(1080,1350),canonical_assets_equal=False).status,'VISUAL_REGRESSION_FAIL')

    def test_dimension_or_count_drift_hard_fails(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/'a.png'; b=Path(td)/'b.png'; Image.new('RGB',(1080,1350)).save(a); Image.new('RGB',(100,100)).save(b)
            self.assertEqual(compare_series([a],[b],expected_size=(1080,1350)).status,'VISUAL_REGRESSION_FAIL')
            self.assertEqual(compare_series([a],[],expected_size=(1080,1350)).status,'VISUAL_REGRESSION_FAIL')

    def test_golden_schema(self): self.assertEqual(len(self.golden().to_row()),15)

    def golden(self):
        return create_golden_candidate(golden_id='G1',now=NOW,archive_id='AR1',asset_id='A1',master_id='M1',platform='INSTAGRAM',output_type='CAROUSEL',role_or_series='SERIES',quality_reason='strong',baseline_renderer_version='1',baseline_manifest_ref='manifest://1',human_nominated=True)

if __name__=='__main__': unittest.main()
