import copy,unittest
from analyze_l3 import metric

def rows(masses):return [dict(t_over_tcc=t,dense_mass=m) for t,m in zip([0,2.5,5],masses)]
class MetricTests(unittest.TestCase):
    def test_fixed_initial_mass(self):self.assertAlmostEqual(metric(rows([10,5,2]),rows([10,7,3]))['peak_curve_difference_over_initial_mass'],.2)
    def test_changed_initial_mass_rejected(self):
        with self.assertRaises(ValueError):metric(rows([10,5,2]),rows([20,7,3]))
    def test_incomplete_interval_rejected(self):
        a=rows([10,5,2]);a[-1]['t_over_tcc']=4
        with self.assertRaises(ValueError):metric(a,rows([10,7,3]))
    def test_actual_times_not_modified(self):
        a=rows([10,5,2]);before=copy.deepcopy(a);metric(a,a);self.assertEqual(a,before)

if __name__=='__main__':unittest.main()
