import copy,unittest
import numpy as np
from analyze_mfm_levels import scalar_curve,pair_metric,accept_cases

def rows(values):
    return [dict(t_over_tcc=float(t),dense_mass=float(m)) for t,m in zip(np.linspace(0,5,len(values)),values)]

class AnalysisTests(unittest.TestCase):
    def test_fixed_initial_denominator(self):
        a=rows([10,5,2]);b=rows([10,7,3]);metric=pair_metric(a,b)
        self.assertAlmostEqual(metric['peak_curve_difference_over_initial_mass'],.2)
        self.assertEqual(metric['final_dense_fractions'],[.2,.3])
    def test_different_initial_denominators_rejected(self):
        with self.assertRaises(ValueError):pair_metric(rows([10,5]),rows([20,5]))
    def test_missing_terminal_interval_rejected(self):
        a=rows([10,5]);a[-1]['t_over_tcc']=4
        with self.assertRaises(ValueError):scalar_curve(a,10)
    def test_native_rows_not_modified(self):
        a=rows([10,5,2]);old=copy.deepcopy(a);scalar_curve(a,10);self.assertEqual(a,old)
    def test_exact_duplicate_conflict_rejected(self):
        a=rows([10,5,2]);a.insert(1,dict(t_over_tcc=0,dense_mass=9))
        with self.assertRaises(ValueError):scalar_curve(a,10)
    def test_running_or_failed_l4_not_accepted(self):
        for status in ('running','needs_review'):
            with self.assertRaises(ValueError):accept_cases(dict(status=status,finished=[]),4)

if __name__=='__main__':unittest.main()
