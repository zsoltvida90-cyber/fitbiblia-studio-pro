import unittest

from content_os.campaigns.campaign_engine import (
    CampaignError, campaign_balance, can_launch_campaign, dossier_readiness,
    productization_gate, threaded_feed_share, validate_campaign,
    validate_campaign_asset, validate_product_authority_sources,
    validate_topic_hub, validate_topic_node,
)


class CampaignEngineTests(unittest.TestCase):
    def hub(self, **kw):
        d = {"topic_hub_id":"H1","title":"Sleep","dossier_ref":"drive://d","dossier_version":"0.1","research_status":"MAPPING","campaign_readiness":"NOT_READY"}
        d.update(kw); return d

    def node(self, **kw):
        d = {"node_id":"N1","topic_hub_id":"H1","title":"Duration","research_question":"How much?","research_status":"RESEARCH_NEEDED","human_priority":"HIGH"}
        d.update(kw); return d

    def campaign(self, **kw):
        d = {"campaign_id":"C1","topic_hub_id":"H1","title":"Sleep campaign","status":"DRAFT_RESEARCH_DEPENDENT","campaign_weeks":4}
        d.update(kw); return d

    def asset(self, **kw):
        d = {"campaign_asset_id":"A1","campaign_id":"C1","topic_hub_id":"H1","node_id":"N1","objective":"SAVE","status":"RESEARCH_DEPENDENT","wave":"W1","output_type":"CAROUSEL"}
        d.update(kw); return d

    def test_hub_requires_dossier(self):
        with self.assertRaisesRegex(CampaignError,"DOSSIER_REF_REQUIRED"):
            validate_topic_hub(self.hub(dossier_ref=""))

    def test_hub_ready_requires_dossier_ready(self):
        with self.assertRaisesRegex(CampaignError,"CAMPAIGN_READINESS_REQUIRES_DOSSIER_READY"):
            validate_topic_hub(self.hub(campaign_readiness="READY"))

    def test_resolved_node_requires_provenance(self):
        with self.assertRaisesRegex(CampaignError,"RESOLVED_NODE_REQUIRES_PROVENANCE"):
            validate_topic_node(self.node(research_status="VALIDATED"))

    def test_dossier_not_ready_with_gaps(self):
        r=dossier_readiness([self.node()])
        self.assertFalse(r["dossier_ready"]); self.assertEqual(r["coverage_ratio"],0.0)

    def test_dossier_ready_when_nodes_resolved(self):
        r=dossier_readiness([self.node(research_status="EVIDENCE_LIMITED")])
        self.assertTrue(r["dossier_ready"])

    def test_campaign_active_requires_human(self):
        with self.assertRaisesRegex(CampaignError,"HUMAN_CAMPAIGN_APPROVAL_REQUIRED"):
            validate_campaign(self.campaign(status="ACTIVE",start_date="2026-09-01"),dossier_ready=True,human_approved=False)

    def test_campaign_active_requires_dossier(self):
        with self.assertRaisesRegex(CampaignError,"DOSSIER_NOT_READY"):
            validate_campaign(self.campaign(status="ACTIVE",start_date="2026-09-01"),dossier_ready=False,human_approved=True)

    def test_asset_objective_required(self):
        with self.assertRaisesRegex(CampaignError,"OBJECTIVE_INVALID"):
            validate_campaign_asset(self.asset(objective="EVERYTHING"))

    def test_asset_cannot_advance_before_node_research(self):
        with self.assertRaisesRegex(CampaignError,"NODE_RESEARCH_REQUIRED"):
            validate_campaign_asset(self.asset(status="READY_FOR_MASTER"),node=self.node())

    def test_mastered_asset_requires_master(self):
        with self.assertRaisesRegex(CampaignError,"MASTER_AUTHORITY_REQUIRED"):
            validate_campaign_asset(self.asset(status="MASTERED"))

    def test_threaded_share(self):
        self.assertEqual(threaded_feed_share(campaign_social_per_week=3,flex_social_per_week=2),0.6)

    def test_social_only_cannot_authorize_product(self):
        with self.assertRaisesRegex(CampaignError,"PRODUCT_SOURCE_AUTHORITY_INVALID"):
            validate_product_authority_sources(["CAROUSEL","REEL"])

    def test_dossier_plus_social_is_valid_authority(self):
        r=validate_product_authority_sources(["TOPIC_DOSSIER","CAROUSEL"])
        self.assertTrue(r["authority_ok"])

    def test_productization_waits_for_human(self):
        r=productization_gate(dossier_ready=True,claim_integrity_ok=True,unique_value_defined=True,human_product_decision=False)
        self.assertEqual(r["status"],"READY_FOR_HUMAN_PRODUCT_DECISION")

    def test_productization_blocked_by_missing_integrity(self):
        r=productization_gate(dossier_ready=True,claim_integrity_ok=False,unique_value_defined=True,human_product_decision=True)
        self.assertEqual(r["status"],"NOT_READY")

    def test_balance_detects_monotony(self):
        rows=[self.asset(campaign_asset_id=f"A{i}") for i in range(6)]
        r=campaign_balance(rows)
        self.assertIn("OBJECTIVE_MONOTONY",r["warnings"])
        self.assertIn("FORMAT_MONOTONY",r["warnings"])

    def test_launch_rejects_unresearched_dossier(self):
        with self.assertRaisesRegex(CampaignError,"DOSSIER_NOT_READY"):
            can_launch_campaign(hub=self.hub(),nodes=[self.node()],campaign=self.campaign(status="APPROVED"),assets=[self.asset()],human_approved=True)


if __name__ == "__main__":
    unittest.main()
