import unittest
from datetime import datetime,timezone
from content_os.experiments.experiment_engine import *
from content_os.performance.objective_engine import ObjectiveResult
NOW=datetime(2026,8,14,11,55,tzinfo=timezone.utc)
LATER=datetime(2026,8,15,11,55,tzinfo=timezone.utc)

def r(value,status='OK',objective='SAVE',metric='SAVE_RATE'):
    return ObjectiveResult(objective,metric,value,'saves','reach',50,1000,status,'x')
class ExperimentTests(unittest.TestCase):
    def exp(self,**kw):
        d=dict(experiment_id='EXP-1',now=NOW,master_id='M1',hypothesis='Hook B increases saves',objective='SAVE',primary_metric='SAVE_RATE',platform='INSTAGRAM',output_type='CAROUSEL',variant_a_asset_id='A',variant_b_asset_id='B',changed_dimension='HOOK',control_notes='same master, copy body, CTA and publish window',master_approved=True,claims_equal=True);d.update(kw);return create_experiment(**d)
    def test_master_authority_required(self):
        with self.assertRaisesRegex(PermissionError,'MASTER_AUTHORITY_REQUIRED'):self.exp(master_approved=False)
    def test_claim_drift_blocked(self):
        with self.assertRaisesRegex(PermissionError,'EXPERIMENT_CLAIM_DRIFT'):self.exp(claims_equal=False)
    def test_variant_ids_distinct(self):
        with self.assertRaisesRegex(ValueError,'EXPERIMENT_VARIANTS_INVALID'):self.exp(variant_b_asset_id='A')
    def test_one_dimension_contract(self):
        with self.assertRaisesRegex(ValueError,'EXPERIMENT_DIMENSION_INVALID'):self.exp(changed_dimension='EVERYTHING')
    def test_control_notes_required(self):
        with self.assertRaisesRegex(ValueError,'EXPERIMENT_CONTROL_REQUIRED'):self.exp(control_notes='')
    def test_start_requires_both_distribution_ready(self):
        e=self.exp()
        with self.assertRaisesRegex(PermissionError,'DISTRIBUTION_AUTHORITY_REQUIRED'):start_experiment(e,now=NOW,distribution_ready_a=True)
        self.assertEqual(start_experiment(e,now=NOW,distribution_ready_a=True,distribution_ready_b=True).status,'RUNNING')
    def test_finish_requires_running(self):
        with self.assertRaisesRegex(PermissionError,'EXPERIMENT_STATUS_INVALID'):finish_experiment(self.exp(),now=LATER,result_a=r(5),result_b=r(6),sample_context='x')
    def test_objective_mismatch(self):
        e=start_experiment(self.exp(),now=NOW,distribution_ready_a=True,distribution_ready_b=True)
        with self.assertRaisesRegex(ValueError,'OBJECTIVE_MISMATCH'):finish_experiment(e,now=LATER,result_a=r(5),result_b=r(6,objective='FOLLOW'),sample_context='x')
    def test_metric_mismatch(self):
        e=start_experiment(self.exp(),now=NOW,distribution_ready_a=True,distribution_ready_b=True)
        with self.assertRaisesRegex(ValueError,'EXPERIMENT_METRIC_MISMATCH'):finish_experiment(e,now=LATER,result_a=r(5),result_b=r(6,metric='SHARE_RATE'),sample_context='x')
    def test_observational_is_low_confidence_descriptive(self):
        e=start_experiment(self.exp(),now=NOW,distribution_ready_a=True,distribution_ready_b=True);e=finish_experiment(e,now=LATER,result_a=r(5),result_b=r(6),sample_context='similar reach',design='OBSERVATIONAL');self.assertEqual(e.status,'COMPLETE');self.assertEqual(e.confidence,'LOW');self.assertIn('DESCRIPTIVE_SIGNAL',e.result);self.assertIn('not causal proof',e.notes)
    def test_platform_randomized_still_not_significance_claim(self):
        e=start_experiment(self.exp(),now=NOW,distribution_ready_a=True,distribution_ready_b=True);e=finish_experiment(e,now=LATER,result_a=r(5),result_b=r(6),sample_context='platform A/B',design='PLATFORM_RANDOMIZED');self.assertEqual(e.confidence,'MEDIUM');self.assertIn('separate statistical-significance',e.notes)
    def test_unknown_result_insufficient(self):
        e=start_experiment(self.exp(),now=NOW,distribution_ready_a=True,distribution_ready_b=True);e=finish_experiment(e,now=LATER,result_a=r(None,'UNKNOWN'),result_b=r(6),sample_context='x');self.assertEqual(e.result,'INSUFFICIENT_DATA')
    def test_learning_link_after_complete(self):
        e=start_experiment(self.exp(),now=NOW,distribution_ready_a=True,distribution_ready_b=True);e=finish_experiment(e,now=LATER,result_a=r(5),result_b=r(6),sample_context='x');self.assertEqual(link_learning(e,'LEARN-1').learning_id,'LEARN-1')
    def test_id_and_schema(self):
        self.assertEqual(next_experiment_id(['EXP-20260814-001','EXP-20260814-004'],NOW),'EXP-20260814-005');self.assertEqual(len(self.exp().to_row()),20)
if __name__=='__main__':unittest.main()
