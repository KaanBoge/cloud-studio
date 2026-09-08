import unittest
import numpy as np
from native_cadence import expected_times,cadence

class CadenceTests(unittest.TestCase):
    def setUp(self):
        self.p={'t_cc':3.872983346207417};self.v={'OutputListOn':'0','ComovingIntegrationOn':'0','TimeBegin':'0','TimeMax':format(5*self.p['t_cc'],'.17g'),'TimeOfFirstSnapshot':'0','TimeBetSnapshot':format(self.p['t_cc']/20,'.17g'),'MaxSizeTimestep':'.05'}
    def test_both_early_and_late_native_times(self):
        times,unit,block=expected_times(self.v);delta=times-np.linspace(0,5*self.p['t_cc'],101)
        self.assertTrue(np.any(delta<0));self.assertTrue(np.any(delta>0));cadence(times,self.p,self.v)
    def test_shifted_frame_rejected(self):
        times,_,_=expected_times(self.v);times[2]+=.00001
        with self.assertRaises(ValueError):cadence(times,self.p,self.v)
    def test_missing_state_rejected(self):
        times,_,_=expected_times(self.v)
        with self.assertRaises(ValueError):cadence(times[:-1],self.p,self.v)
    def test_raw_times_not_changed(self):
        times,_,_=expected_times(self.v);before=times.copy();cadence(times,self.p,self.v);np.testing.assert_array_equal(times,before)
    def test_unhandled_compile_mode_rejected(self):
        self.v['OutputListOn']='1'
        with self.assertRaises(ValueError):expected_times(self.v)

if __name__=='__main__':unittest.main()
