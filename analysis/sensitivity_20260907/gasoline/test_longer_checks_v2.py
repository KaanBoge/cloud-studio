import unittest
import numpy as np
import longer_checks_v2 as l

class Tests(unittest.TestCase):
    def test_native_rank_guard(self):
        l.e.validate_ranks({'ranks':2})
        for n in (1,4,8,None):
            with self.assertRaises(ValueError):l.e.validate_ranks({'ranks':n})

    def test_one_spacing(self):
        a=np.array([1.],dtype=np.float32)
        b=np.nextafter(a,np.float32(np.inf))
        self.assertTrue(l.within_spacing(a,b,1)['passed'])
        c=np.nextafter(b,np.float32(np.inf))
        self.assertFalse(l.within_spacing(a,c,1)['passed'])

    def test_zero_velocity_reference_scale(self):
        vw=2*np.sqrt(5/3)
        self.assertTrue(l.within_spacing(np.array([0.]),np.array([1e-14]),vw)['passed'])
        self.assertFalse(l.within_spacing(np.array([0.]),np.array([1e-4]),vw)['passed'])

    def test_periodic_error_kept_separate(self):
        r=l.within_spacing(np.array([-10.]),np.array([10.]),.3125,20.)
        self.assertTrue(r['passed']);self.assertEqual(r['max_direct_absolute'],20.)
        self.assertEqual(r['max_absolute'],0.)

    def test_small_energy_floor(self):
        bound=l.spacing_limit(np.array([0.]),np.array([0.]),.015)
        self.assertEqual(float(bound[0]),float(np.spacing(np.float32(.015))))

    def test_fail_nonfinite(self):
        self.assertFalse(l.within_spacing(np.array([np.nan]),np.array([1.]),1)['passed'])

if __name__=='__main__':unittest.main()
