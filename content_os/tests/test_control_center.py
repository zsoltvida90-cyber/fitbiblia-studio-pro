import unittest
from datetime import datetime,timezone
from content_os.control.control_center import *
NOW=datetime(2026,8,14,12,0,tzinfo=timezone.utc)

class ControlCenterTests(unittest.TestCase):
    def test_ready_idea_requires_human(self):
        c=build_cards(now=NOW,idea_rows=[{'idea_id':'I1','title':'x','status':'READY_FOR_DECISION','priority_score':90}]);self.assertEqual(c[0].section,'DECIDE_IDEA');self.assertEqual(c[0].human_action_required,'YES')
    def test_duplicate_deferred_has_reuse_gate(self):
        c=build_cards(now=NOW,idea_rows=[{'idea_id':'I1','title':'x','status':'DEFERRED','duplicate_status':'DUPLICATE'}]);self.assertEqual(c[0].blocker_code,'DUPLICATE_REUSE_APPROVAL_REQUIRED')
    def test_human_review_queue(self):
        c=build_cards(now=NOW,queue_rows=[{'queue_id':'Q1','title':'x','stage':'HUMAN_REVIEW','priority':70}]);self.assertEqual(c[0].section,'REVIEW_PRODUCT');self.assertEqual(c[0].human_action_required,'YES')
    def test_archived_planned_is_publication_decision_not_published(self):
        c=build_cards(now=NOW,queue_rows=[{'queue_id':'Q1','title':'x','stage':'ARCHIVED','publication_status':'PLANNED'}]);self.assertEqual(c[0].section,'READY_FOR_PUBLICATION_DECISION');self.assertIn('DISTRIBUTION_LOG',c[0].authority_note)
    def test_queue_working_is_nonhuman(self):
        c=build_cards(now=NOW,queue_rows=[{'queue_id':'Q1','title':'x','stage':'RENDERING'}]);self.assertEqual(c[0].section,'AI_WORKING');self.assertEqual(c[0].human_action_required,'NO')
    def test_blocker_human_detection(self):
        c=build_cards(now=NOW,queue_rows=[{'queue_id':'Q1','title':'x','stage':'QA','blocker_code':'HEALTH_RISK_REVIEW_REQUIRED'}]);self.assertEqual(c[0].section,'BLOCKED');self.assertEqual(c[0].human_action_required,'YES')
    def test_feedback_only_hypothesis_surfaces(self):
        rows=[{'feedback_id':'F1','rule_status':'OBSERVATION','candidate_rule':'a'},{'feedback_id':'F2','rule_status':'HYPOTHESIS','candidate_rule':'b','feedback_type':'VISUAL'}];c=build_cards(now=NOW,feedback_rows=rows);self.assertEqual(len(c),1);self.assertEqual(c[0].item_ref,'F2')
    def test_science_feedback_routes_science_review(self):
        c=build_cards(now=NOW,feedback_rows=[{'feedback_id':'F','rule_status':'HYPOTHESIS','candidate_rule':'x','feedback_type':'SCIENCE_WORDING'}]);self.assertEqual(c[0].blocker_code,'SCIENCE_POLICY_REVIEW_REQUIRED')
    def test_golden_candidate_surfaces(self):
        c=build_cards(now=NOW,golden_rows=[{'golden_id':'G1','status':'CANDIDATE','quality_reason':'strong'}]);self.assertEqual(c[0].section,'REVIEW_GOLDEN')
    def test_complete_experiment_without_learning_surfaces(self):
        c=build_cards(now=NOW,experiment_rows=[{'experiment_id':'E1','status':'COMPLETE','hypothesis':'h','learning_id':''}]);self.assertEqual(c[0].section,'EXPERIMENT_LEARNING')
    def test_failed_run_prioritized(self):
        c=build_cards(now=NOW,run_rows=[{'run_id':'R1','status':'FAIL','operation':'x','error_code':'TOOL_FAILURE','human_action_required':'NO'}],queue_rows=[{'queue_id':'Q1','title':'x','stage':'RENDERING'}]);self.assertEqual(c[0].section,'SYSTEM_ISSUE')
    def test_audience_recurring_unlinked_surfaces_once_per_cluster(self):
        rows=[{'signal_id':'S1','cluster_key':'C','recurrence_state':'RECURRING','normalized_problem':'p','linked_idea_id':''},{'signal_id':'S2','cluster_key':'C','recurrence_state':'RECURRING','normalized_problem':'p','linked_idea_id':''}];c=build_cards(now=NOW,audience_rows=rows);self.assertEqual(len(c),1);self.assertEqual(c[0].section,'AUDIENCE_OPPORTUNITY')
    def test_linked_audience_cluster_hidden(self):
        c=build_cards(now=NOW,audience_rows=[{'signal_id':'S','cluster_key':'C','recurrence_state':'VALIDATED_PATTERN','linked_idea_id':'I1'}]);self.assertEqual(c,[])
    def test_summary_read_model_warning(self):
        cards=build_cards(now=NOW,idea_rows=[{'idea_id':'I1','status':'READY_FOR_DECISION'}]);s=summarize(cards);self.assertEqual(s['authority'],'READ_MODEL_ONLY');self.assertEqual(s['human_action_count'],1);self.assertIn('override',s['warning'])
    def test_sheet_schema(self):
        cards=build_cards(now=NOW,idea_rows=[{'idea_id':'I1','status':'READY_FOR_DECISION'}]);rows=rows_for_sheet(cards);self.assertEqual(rows[0],CONTROL_CENTER_COLUMNS);self.assertEqual(len(rows[1]),13)
if __name__=='__main__':unittest.main()
