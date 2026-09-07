import unittest
import numpy as np
from analyze_athw import mass_metrics,no_mode
class Tests(unittest.TestCase):
    def test_strict_threshold_and_tracer_weight(self):
        d=dict(rho=np.array([1.,3.,6.]),dv=np.array([2.,1.,.5]),tracer=np.array([0.,.2,1.]))
        m,t=mass_metrics(d,3.)
        self.assertEqual(m,3.);self.assertAlmostEqual(t,3.6)
    def test_mode_removal_only(self):
        self.assertEqual(no_mode('a=4\nvelocity_ic_tanh = 1\n'),'a=4\n\n')
    def test_duplicate_or_missing_mode_rejected(self):
        for s in ('a=4','velocity_ic_tanh = 0\nvelocity_ic_tanh = 1'):
            with self.assertRaises(ValueError):no_mode(s)
if __name__=='__main__':unittest.main()
