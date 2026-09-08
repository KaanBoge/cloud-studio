import json,unittest
import numpy as np
from audit_snapshot_timing import scaling_check

class TimingTest(unittest.TestCase):
    def test_native_hdf5_reader_registered(self):
        from yt.utilities.io_handler import io_registry
        from verify_gizmo import IOHandlerGadgetHDF5
        self.assertIs(io_registry['gadget_hdf5'],IOHandlerGadgetHDF5)
    def test_staggered_kick(self):
        initial=np.array([[0.,2.582,0.]],dtype=np.float32)
        dv=np.array([[.0001,-.0002,.00005]])
        result=scaling_check(initial,(initial+dv).astype('f4'),(initial+dv/2).astype('f4'))
        self.assertAlmostEqual(result['norm_ratio'],.5,places=3)
        json.dumps(result,allow_nan=False)
    def test_fixed_ic_error_is_not_a_kick(self):
        initial=np.zeros((2,3));wrong=initial+.01
        with self.assertRaises(ValueError):scaling_check(initial,wrong+.0001,wrong+.00005)
    def test_wrong_scaling_rejected(self):
        initial=np.zeros((2,3))
        with self.assertRaises(ValueError):scaling_check(initial,initial+.001,initial+.0008)
    def test_empty_effect_rejected(self):
        initial=np.zeros((2,3))
        with self.assertRaises(ValueError):scaling_check(initial,initial,initial)

if __name__=='__main__':unittest.main()
