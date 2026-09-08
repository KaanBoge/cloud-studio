import unittest,tempfile
from pathlib import Path
import numpy as np
from run_arepo import input_for,native_params,physics,check_ic,native_snapshots

class NativeControls(unittest.TestCase):
    def test_physics_metadata_and_cadence(self):
        p=physics();v=native_params(input_for(3))
        self.assertAlmostEqual(float(v['TimeMax'])/p['t_cc'],5)
        self.assertAlmostEqual(float(v['TimeBetSnapshot'])/p['t_cc'],.05)
        self.assertEqual(p['seed'],42)
    def test_native_boundaries_and_no_cooling_preserved(self):
        for level in (3,4):
            v=native_params(input_for(level))
            self.assertEqual(v['PeriodicBoundariesOn'],'1');self.assertEqual(v['CoolingOn'],'0')
            self.assertEqual(v['CpuTimeBetRestartFile'],'9000')
            self.assertAlmostEqual(float(v['CourantFac']),.3)
    def test_invalid_level(self):
        with self.assertRaises(ValueError):input_for(6)
    def test_duplicate_parameter_rejected(self):
        with self.assertRaises(ValueError):native_params('BoxSize 10\nBoxSize 20\n')
    def test_malformed_parameter_rejected(self):
        with self.assertRaises(ValueError):native_params('TimeMax\n')
    def test_native_memory_budget_preserved(self):
        self.assertEqual(native_params(input_for(3))['MaxMemSize'],'512')
        self.assertEqual(native_params(input_for(4))['MaxMemSize'],'800')
    def test_smoke_longer_than_maximum_timestep(self):
        v=native_params(input_for(3,True))
        self.assertLess(float(v['MaxSizeTimestep']),float(v['TimeMax'])-float(v['TimeBegin']))
    def test_analysis_sidecars_not_counted_as_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('snap_000.hdf5','snap_000.hsml.hdf5','snap_001.hdf5'):(root/name).touch()
            self.assertEqual(sorted(p.name for p in native_snapshots(root)),['snap_000.hdf5','snap_001.hdf5'])
            (root/'snap_malformed.hdf5').touch()
            with self.assertRaises(ValueError):native_snapshots(root)

if __name__=='__main__':unittest.main()
