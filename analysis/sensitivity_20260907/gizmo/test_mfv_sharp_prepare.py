import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import mfv_sharp_prepare as s


class Tests(unittest.TestCase):
    def params(self):return dict(TimeBegin='0',TimeMax='.1',TimeBetSnapshot='.1',TimeOfFirstSnapshot='0',ComovingIntegrationOn='0')
    def test_clock60(self):
        times,tick=s.clock(self.params());self.assertEqual(tick,.1/(1<<60));self.assertEqual(times,[0.,.1]);s.cadence(times,self.params())
    def test_clock_bad_order(self):
        with self.assertRaises(ValueError):s.cadence([.1,0],self.params())
    def test_clock_missing(self):
        with self.assertRaises(ValueError):s.cadence([0],self.params())
    def test_duplicate_terminal_retained(self):self.assertEqual(s.cadence([0,.1,.1],self.params())['actual_count'],3)
    def test_fields_same(self):self.assertTrue(s.same_fields({'x':np.array([1])},{'x':np.array([1])})['x'])
    def test_fields_differ(self):
        with self.assertRaises(ValueError):s.same_fields({'x':np.array([1])},{'x':np.array([2])})
    def test_dtype_differ(self):
        with self.assertRaises(ValueError):s.same_fields({'x':np.array([1],dtype='f4')},{'x':np.array([1],dtype='f8')})
    def test_scaling(self):self.assertAlmostEqual(s.scaling(np.zeros(2),np.ones(2)*1e-4,np.ones(2)*5e-5)['norm_ratio'],.5)
    def test_fixed_velocity_error(self):
        with self.assertRaises(ValueError):s.scaling(np.zeros(2),np.ones(2)*1e-4,np.ones(2)*1e-4)
    def test_json_numpy(self):self.assertEqual(json.loads(json.dumps(s.safe({'x':np.bool_(True),'v':np.float64(1)}))),{'x':True,'v':1})
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.json';s.save(p,{'first':True})
            with self.assertRaises(FileExistsError):s.save(p,{'first':False})
    def test_budget(self):self.assertGreater(s.budget(5000000,51000000,2400000,True),s.budget(5000000,51000000,2400000))
    def test_mass_failure(self):self.assertFalse(s.short.mass_account(np.ones(10),np.ones(10)*2,np.zeros(10),5)['passes'])
    def test_mass_account(self):self.assertTrue(s.short.mass_account(np.ones(10),np.ones(10)*1.01,np.ones(10)*-.01,5)['passes'])
    def test_storage_fail(self):
        with self.assertRaises(RuntimeError):s.require_storage({'effective_free_bytes':10*s.GIB},1)
    def test_mass_step_envelope(self):
        with self.assertRaises(ValueError):s.short.mass_account(np.ones(2),np.ones(2),np.zeros(2),257)


if __name__=='__main__':unittest.main()
