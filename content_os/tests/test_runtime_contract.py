import importlib.util
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

dedup = load(ROOT/'semantic'/'dedup.py', 'dedup')
learning = load(ROOT/'learning'/'learning_engine.py', 'learning')

class DedupTests(unittest.TestCase):
    def test_exact_duplicate(self):
        a={'topic':'kreatin','problem':'mikor vegyem be','core_thesis':'a kreatin idozitese kevesbe fontos mint a rendszeres szedes','angle':'gyakorlat'}
        self.assertEqual(dedup.compare(a,a).status,'DUPLICATE')
    def test_hunger_paraphrase(self):
        a={'topic':'fogyas','problem':'esti farkasehseg','core_thesis':'az esti ehseg gyakran a napkozbeni alacsony telitettseg kovetkezmenye','angle':'valos elet'}
        b={'topic':'fat loss','problem':'esti ehseg','core_thesis':'az esti ehseg lehet a napkozbeni alacsony telitettseg kovetkezmenye','angle':'real life'}
        self.assertIn(dedup.compare(a,b).status, {'DUPLICATE','RELATED'})
    def test_creatine_bilingual_neighbor(self):
        a={'topic':'kreatin','problem':'edzes elott vagy utan','core_thesis':'a rendszeres kreatin bevitel fontosabb mint a pontos idozites','angle':'idozites'}
        b={'topic':'creatine','problem':'before training or after training','core_thesis':'consistent creatine use matters more than exact timing','angle':'timing'}
        self.assertNotEqual(dedup.compare(a,b).status, 'NEW')
    def test_same_topic_different_thesis(self):
        a={'topic':'protein','problem':'napi bevitel','core_thesis':'a napi osszbevitel a fo gyakorlati prioritas','angle':'minimum'}
        b={'topic':'protein','problem':'emesztes','core_thesis':'egyeni tolerancia alapjan valassz feherjeforrast','angle':'tolerancia'}
        self.assertNotEqual(dedup.compare(a,b).status, 'DUPLICATE')

class LearningTests(unittest.TestCase):
    def test_invalid_distribution_rejected(self):
        self.assertEqual(learning.classify(30,'BLOCK','x',['a']).confidence_state,'REJECTED')
    def test_sample_8(self):
        self.assertEqual(learning.classify(8,'OK').confidence_state,'INSUFFICIENT_DATA')
    def test_sample_15(self):
        self.assertEqual(learning.classify(15,'OK').confidence_state,'EARLY_SIGNAL')
    def test_sample_20_ready(self):
        self.assertEqual(learning.classify(20,'OK','mechanism hooks outperform baseline',['a']).confidence_state,'HYPOTHESIS_READY')
    def test_sample_20_missing_hypothesis(self):
        self.assertEqual(learning.classify(20,'OK','',['a']).confidence_state,'INTEGRITY_FAIL')
    def test_science_mutation_forbidden(self):
        with self.assertRaises(ValueError):
            learning.assert_no_science_mutation('claim_status')

if __name__ == '__main__':
    unittest.main()
