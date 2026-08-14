import unittest
from content_os.competitive.benchmark import *

class TestCompetitiveBenchmark(unittest.TestCase):
    def acc(self, **kw):
        d={"cohort_type":"HU_DIRECT","handle":"@x","platform":"INSTAGRAM",
           "captured_at":"2026-08-14T21:00:00+02:00","source_refs":"src"}
        d.update(kw); return d
    def swipe(self, bucket="TOP", **kw):
        d={"swipe_id":"S1","competitor_id":"C1","post_url":"https://example.com/p",
           "captured_at":"2026-08-14T21:00:00+02:00","sample_bucket":bucket,"source_refs":"src",
           "content_access_level":"UNKNOWN"}
        d.update(kw); return d
    def test_account_valid(self): self.assertEqual(validate_account(self.acc())["platform"],"INSTAGRAM")
    def test_bad_cohort(self):
        with self.assertRaisesRegex(BenchmarkError,"COHORT_INVALID"): validate_account(self.acc(cohort_type="X"))
    def test_source_required(self):
        with self.assertRaisesRegex(BenchmarkError,"SOURCE_REF_REQUIRED"): validate_account(self.acc(source_refs=""))
    def test_account_metric_method(self):
        with self.assertRaisesRegex(BenchmarkError,"METRIC_METHOD_REQUIRED"): validate_account(self.acc(follower_count=100))
        self.assertEqual(validate_account(self.acc(follower_count=100,follower_source="tracker"))["platform"],"INSTAGRAM")
    def test_swipe_bucket(self):
        with self.assertRaisesRegex(BenchmarkError,"SAMPLE_BUCKET_INVALID"): validate_swipe(self.swipe("WOW"))
    def test_access_level(self):
        with self.assertRaisesRegex(BenchmarkError,"CONTENT_ACCESS_LEVEL_INVALID"): validate_swipe(self.swipe(content_access_level="MAGIC"))
    def test_full_carousel_format_match(self):
        with self.assertRaisesRegex(BenchmarkError,"CONTENT_ACCESS_FORMAT_MISMATCH"): validate_swipe(self.swipe(format="REEL",content_access_level="FULL_CAROUSEL"))
    def test_swipe_metric_method(self):
        with self.assertRaisesRegex(BenchmarkError,"METRIC_METHOD_REQUIRED"): validate_swipe(self.swipe(engagement_proxy=20))
        r=validate_swipe(self.swipe(engagement_proxy=20,metric_method="likes+comments")); self.assertEqual(r["content_access_level"],"UNKNOWN")
    def test_missing_metric_unknown(self): self.assertEqual(metric_or_unknown(None),"UNKNOWN")
    def test_rpi(self): self.assertEqual(relative_performance_index(20,10),2.0)
    def test_rpi_missing(self): self.assertIsNone(relative_performance_index(None,10))
    def test_rpi_zero_base(self): self.assertIsNone(relative_performance_index(10,0))
    def test_balance(self):
        rows=[self.swipe("TOP") for _ in range(3)]+[self.swipe("MID") for _ in range(4)]+[self.swipe("LOW") for _ in range(3)]
        self.assertTrue(sample_balance(rows)["balanced_minimum_met"])
    def test_pattern_observation(self): self.assertEqual(classify_pattern(4,3),"OBSERVATION")
    def test_pattern_early(self): self.assertEqual(classify_pattern(5,3),"EARLY_SIGNAL")
    def test_pattern_hypothesis(self): self.assertEqual(classify_pattern(15,5),"HYPOTHESIS")
    def test_aggregate_never_auto_policy(self):
        rows=[self.swipe("TOP", swipe_id=f"S{i}", competitor_id=f"C{i%5}") for i in range(15)]
        p=aggregate_pattern(rows,pattern_type="HOOK",pattern_name="diagnostic")
        self.assertFalse(p["auto_policy_adopt"]); self.assertEqual(p["status"],"HYPOTHESIS")
    def test_full_carousel_pattern_requires_full_records(self):
        with self.assertRaisesRegex(BenchmarkError,"FULL_CAROUSEL_SAMPLE_REQUIRED"):
            aggregate_pattern([self.swipe()],pattern_type="VISUAL",pattern_name="x",require_full_carousel=True)
        rows=[self.swipe(format="CAROUSEL",content_access_level="FULL_CAROUSEL",swipe_id=f"S{i}",competitor_id=f"C{i%3}") for i in range(5)]
        p=aggregate_pattern(rows,pattern_type="VISUAL",pattern_name="x",require_full_carousel=True)
        self.assertEqual(p["status"],"EARLY_SIGNAL")
    def test_visual_rule_gate(self):
        self.assertFalse(visual_rule_allowed_from_record(self.swipe(content_access_level="CAPTION_METADATA_ONLY")))
        self.assertTrue(visual_rule_allowed_from_record(self.swipe(content_access_level="FULL_CAROUSEL")))
    def test_competitor_never_science_authority(self): self.assertFalse(science_claim_allowed_from_competitor({}))
    def test_human_approval_gate(self):
        with self.assertRaisesRegex(BenchmarkError,"HUMAN_POLICY_APPROVAL_REQUIRED"): approve_pattern({"status":"HYPOTHESIS"})
        self.assertEqual(approve_pattern({"status":"HYPOTHESIS"},human_approved=True)["status"],"HUMAN_APPROVED")

if __name__=="__main__": unittest.main()
