import unittest
import numpy as np
import verify_longer_2rank as v

class Tests(unittest.TestCase):
    def particles(self):
        a=np.zeros(2,v.g.GAS)
        for k in ('mass','rho','temp','eps'):a[k]=1
        return a

    def test_identical(self):
        a=self.particles();r=v.compare(a,a.copy(),100,5/3)
        self.assertTrue(r['passed']);self.assertTrue(r['all_TIPSY_fields_bitwise_equal'])

    def test_dense_mask_not_hidden_by_field_tolerance(self):
        a=self.particles();b=a.copy();b['rho'][0]=np.nextafter(np.float32(1),np.float32(2))
        r=v.compare(a,b,3,5/3)
        self.assertTrue(r['finite_precision']['rho']['passed'])
        self.assertFalse(r['dense_membership_exact']);self.assertFalse(r['passed'])

    def test_mass_exact_requirement(self):
        a=self.particles();b=a.copy();b['mass'][0]=np.nextafter(np.float32(1),np.float32(2))
        self.assertFalse(v.compare(a,b,100,5/3)['passed'])

    def test_strict_and_numerical_results_separate(self):
        a=self.particles();b=a.copy();b['vel'][0,1]=1e-14
        r=v.compare(a,b,100,5/3)
        self.assertTrue(r['passed']);self.assertFalse(r['all_TIPSY_fields_bitwise_equal'])

if __name__=='__main__':unittest.main()
