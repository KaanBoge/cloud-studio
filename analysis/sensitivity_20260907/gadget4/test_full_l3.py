import unittest
import numpy as np
from run_full_l3 import full_inputs,cadence

class FullTests(unittest.TestCase):
    def setUp(self):self.p={'t_cc':3.872983346207417};self.v={'MaxSizeTimestep':'.05'}
    def test_all_requested_times(self):self.assertEqual(cadence(np.linspace(0,5*self.p['t_cc'],101),self.p,self.v)['native_snapshots'],101)
    def test_original_sync_delay_allowed(self):
        times=np.linspace(0,5*self.p['t_cc'],101);times[1:-1]+=.01;cadence(times,self.p,self.v)
    def test_missing_snapshot_rejected(self):
        with self.assertRaises(ValueError):cadence(np.linspace(0,5*self.p['t_cc'],100),self.p,self.v)
    def test_retains_extra_terminal(self):
        times=np.linspace(0,5*self.p['t_cc'],101);self.assertEqual(cadence(np.append(times,times[-1]),self.p,self.v)['native_snapshots'],102)
    def test_incomplete_time_rejected(self):
        with self.assertRaises(ValueError):cadence(np.linspace(0,4*self.p['t_cc'],101),self.p,self.v)
    def test_full_numerics_unchanged(self):
        text='MaxMemSize 1000\nMaxSizeTimestep 0.05\nCourantFac 0.15\nMinEgySpec 0\nCpuTimeBetRestartFile 7200\nDesNumNgb 64'
        values=full_inputs(text,self.p);self.assertEqual(values['MaxSizeTimestep'],'0.05');self.assertEqual(values['DesNumNgb'],'64');self.assertEqual(values['CpuTimeBetRestartFile'],'7200')
    def test_diagnostic_step_rejected(self):
        with self.assertRaises(ValueError):full_inputs('MaxMemSize 1000\nMaxSizeTimestep 0.00001\nCourantFac 0.15\nMinEgySpec 0\nCpuTimeBetRestartFile 7200',self.p)

if __name__=='__main__':unittest.main()
