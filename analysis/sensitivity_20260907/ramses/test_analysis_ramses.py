import unittest
import numpy as np
from analyze_ramses import second_aggregation

class NativeSums(unittest.TestCase):
    def test_volume_threshold_and_tracer(self):
        c=np.zeros((3,10));c[:,3]=[1,2,.5];c[:,4]=[100,100/3,40];c[:,9]=[1,.2,.5]
        result=second_aggregation(c,dict(chi=100,rho_wind=1))
        self.assertAlmostEqual(result['dense_mass'],105)
        self.assertAlmostEqual(result['total_mass'],100+8*100/3+5)
        self.assertAlmostEqual(result['tracer_mass'],100+8*100/3*.2+2.5)
    def test_bad_native_field_rejected(self):
        c=np.zeros((2,10));c[0,4]=np.nan
        with self.assertRaises(ValueError):second_aggregation(c,dict(chi=100,rho_wind=1))

if __name__=='__main__':unittest.main()
