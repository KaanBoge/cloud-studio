import unittest
import mfv_sharp_full as f


class Tests(unittest.TestCase):
    def rows(self,end=5,mass=1):return [{'time_code':0,'dense_mass':1},{'time_code':end,'dense_mass':mass}]
    def test_equal(self):self.assertEqual(f.mass_comparison(self.rows(),self.rows(),1)['maximum_absolute_separation_fraction'],0)
    def test_fixed_denominator(self):self.assertAlmostEqual(f.mass_comparison(self.rows(mass=.5),self.rows(mass=.8),1)['maximum_absolute_separation_fraction'],.3)
    def test_different_denominator(self):
        rows=self.rows();rows[0]['dense_mass']=2
        with self.assertRaises(ValueError):f.mass_comparison(rows,self.rows(),1)
    def test_incomplete(self):
        with self.assertRaises(ValueError):f.mass_comparison(self.rows(4),self.rows(),1)
    def test_mass_negative(self):
        with self.assertRaises(ValueError):f.mass_comparison(self.rows(mass=-1),self.rows(),1)
    def test_step_envelope(self):
        import numpy as np
        with self.assertRaises(ValueError):f.p.onset.mass_account(np.ones(2),np.ones(2),np.zeros(2),32769)
    def test_full_clock(self):
        params=dict(TimeBegin='0',TimeMax='19.364916731037084',TimeBetSnapshot='.19364916731037085',TimeOfFirstSnapshot='0',ComovingIntegrationOn='0')
        times,tick=f.p.clock(params);self.assertEqual(len(times),101);self.assertEqual(f.p.cadence(times,params)['bits'],60)


if __name__=='__main__':unittest.main()
