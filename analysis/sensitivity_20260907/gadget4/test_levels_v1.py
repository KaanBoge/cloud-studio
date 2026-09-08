import copy
import unittest
from analyze_levels_v1 import curve, metrics, scalar_interp


def rows():
    return [dict(t_over_tcc=i*.05,dense_mass=10-i*.05) for i in range(101)]


class ScalarTests(unittest.TestCase):
    def test_equal_curves(self):
        self.assertEqual(metrics(rows(),rows())['peak_curve_difference_over_initial_mass'],0)
    def test_fixed_denominator(self):
        a,b=rows(),rows();b[-1]['dense_mass']=4
        self.assertAlmostEqual(metrics(a,b)['peak_curve_difference_over_initial_mass'],.1)
    def test_different_initial_fails(self):
        b=rows();b[0]['dense_mass']=9
        with self.assertRaises(ValueError): metrics(rows(),b)
    def test_missing_state_fails(self):
        with self.assertRaises(ValueError): curve(rows()[:-1])
    def test_duplicate_time_fails(self):
        b=rows();b[1]['t_over_tcc']=0
        with self.assertRaises(ValueError): curve(b)
    def test_incomplete_end_fails(self):
        b=rows();b[-1]['t_over_tcc']=4.99
        with self.assertRaises(ValueError): curve(b)
    def test_nonfinite_fails(self):
        b=rows();b[1]['dense_mass']=float('nan')
        with self.assertRaises(ValueError): curve(b)
    def test_negative_mass_fails(self):
        b=rows();b[1]['dense_mass']=-1
        with self.assertRaises(ValueError): curve(b)
    def test_zero_denominator_fails(self):
        b=rows();b[0]['dense_mass']=0
        with self.assertRaises(ValueError): curve(b)
    def test_native_off_grid_is_not_rewritten(self):
        b=rows();b[30]['t_over_tcc']+=.005;before=copy.deepcopy(b)
        metrics(rows(),b);self.assertEqual(b,before)
    def test_scalar_linear(self):
        self.assertEqual(scalar_interp([0,2],[1,5],1),3)
    def test_scalar_endpoint(self):
        self.assertEqual(scalar_interp([0,2],[1,5],2),5)


if __name__=='__main__':
    unittest.main(verbosity=2)
