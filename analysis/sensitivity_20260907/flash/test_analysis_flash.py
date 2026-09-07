import unittest
from analyze_flash import curve_delta

class CurveTests(unittest.TestCase):
    def test_fixed_denominator(self):
        a=[dict(t_over_tcc=0,dense_mass_over_initial=1),dict(t_over_tcc=5,dense_mass_over_initial=0)]
        b=[dict(t_over_tcc=0,dense_mass_over_initial=1),dict(t_over_tcc=5,dense_mass_over_initial=.1)]
        self.assertAlmostEqual(curve_delta(a,b),.1)
    def test_incomplete_or_repeated_times_rejected(self):
        for times in ((0,0),(0,4)):
            s=[dict(t_over_tcc=t,dense_mass_over_initial=1) for t in times]
            with self.assertRaises(ValueError):curve_delta(s,s)

if __name__=='__main__':unittest.main()
