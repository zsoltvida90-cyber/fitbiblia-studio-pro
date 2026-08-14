import unittest
from content_os.performance.objective_engine import *

class ObjectiveEngineTests(unittest.TestCase):
    def m(self,**kw):
        d={'metric_integrity_gate':'OK','reach':1000,'profile_visits':100,'follows':20,'saves':50,'shares':25,'comments':10,'link_clicks':40,'leads':8,'profile_visit_rate':10.0}
        d.update(kw);return d
    def test_follow(self): self.assertEqual(evaluate_objective('FOLLOW',self.m()).value,20.0)
    def test_save(self): self.assertEqual(evaluate_objective('SAVE',self.m()).value,5.0)
    def test_share(self): self.assertEqual(evaluate_objective('SHARE',self.m()).value,2.5)
    def test_comment(self): self.assertEqual(evaluate_objective('COMMENT',self.m()).value,1.0)
    def test_missing_denominator_unknown(self): self.assertEqual(evaluate_objective('SAVE',self.m(reach='')).status,'UNKNOWN')
    def test_zero_denominator_unknown(self): self.assertEqual(evaluate_objective('FOLLOW',self.m(profile_visits=0)).status,'UNKNOWN')
    def test_trust_requires_proxy(self):
        with self.assertRaisesRegex(ValueError,'TRUST_PROXY_REQUIRED'): evaluate_objective('TRUST',self.m())
        r=evaluate_objective('TRUST',self.m(),trust_proxy_key='profile_visit_rate');self.assertEqual(r.value,10.0);self.assertIn('not direct trust',r.reason)
    def test_conversion_requires_definition(self):
        with self.assertRaisesRegex(ValueError,'CONVERSION_DEFINITION_REQUIRED'): evaluate_objective('CONVERT',self.m())
        self.assertEqual(evaluate_objective('CONVERT',self.m(),conversion_numerator_key='leads',conversion_denominator_key='link_clicks').value,20.0)
    def test_bad_metric_integrity_blocked(self):
        with self.assertRaisesRegex(PermissionError,'METRIC_INTEGRITY_FAIL'): evaluate_objective('SAVE',self.m(metric_integrity_gate='FAIL'))
    def test_invalid_objective(self):
        with self.assertRaisesRegex(ValueError,'OBJECTIVE_INVALID'): evaluate_objective('VIRAL',self.m())
    def test_cross_objective_compare_blocked(self):
        a=evaluate_objective('SAVE',self.m());b=evaluate_objective('SHARE',self.m())
        with self.assertRaisesRegex(ValueError,'OBJECTIVE_MISMATCH'): compare_results(a,b)
    def test_same_objective_compare(self):
        a=evaluate_objective('SAVE',self.m(saves=20));b=evaluate_objective('SAVE',self.m(saves=50));r=compare_results(a,b);self.assertEqual(r['direction'],'UP');self.assertEqual(r['delta'],3.0)
    def test_unknown_compare_insufficient(self):
        a=evaluate_objective('SAVE',self.m(reach=''));b=evaluate_objective('SAVE',self.m());self.assertEqual(compare_results(a,b)['status'],'INSUFFICIENT_DATA')
if __name__=='__main__':unittest.main()
