import unittest
from analyze_arepo import delta

class CurveChecks(unittest.TestCase):
    def test_fixed_initial_denominator(self):
        a=[dict(t_over_tcc=t,dense_mass_over_initial=m) for t,m in ((0,1),(5,0))]
        b=[dict(t_over_tcc=t,dense_mass_over_initial=m) for t,m in ((0,1),(5,.2))]
        self.assertAlmostEqual(delta(a,b),.2)
    def test_incomplete_duplicate_nan_rejected(self):
        for times in ((0,4),(0,0),(0,float('nan'))):
            s=[dict(t_over_tcc=t,dense_mass_over_initial=1) for t in times]
            with self.assertRaises(ValueError):delta(s,s)

if __name__=='__main__':unittest.main()
