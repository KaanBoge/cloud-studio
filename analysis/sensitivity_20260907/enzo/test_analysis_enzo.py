import unittest
from analyze_enzo import curve_delta
class Tests(unittest.TestCase):
    def test_fixed_mass_difference(self):
        a=[dict(t_over_tcc=t,dense_mass_over_initial=m) for t,m in ((0,1),(5,0))]
        b=[dict(t_over_tcc=t,dense_mass_over_initial=m) for t,m in ((0,1),(5,.1))]
        self.assertAlmostEqual(curve_delta(a,b),.1)
    def test_repeated_time_rejected(self):
        s=[dict(t_over_tcc=0,dense_mass_over_initial=1)]*2
        with self.assertRaises(ValueError):curve_delta(s,s)
if __name__=='__main__':unittest.main()
