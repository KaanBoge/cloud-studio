import unittest
import mfv_l4_full as f


class FullTests(unittest.TestCase):
    def test_unfinished_preparation_rejected(self):
        with self.assertRaises(ValueError):f.admission({'status':'running'})
    def test_wrong_preparation_scope(self):
        with self.assertRaises(ValueError):f.admission({'status':'passed_L4_short_preparation_not_full_pair','cases':[]})
    def test_identical_full_parameters(self):f.inputs_equal('MaxSizeTimestep .05\nCpuTimeBetRestartFile 3600','MaxSizeTimestep .05\nCpuTimeBetRestartFile 3600')
    def test_different_full_parameters(self):
        with self.assertRaises(ValueError):f.inputs_equal('MaxSizeTimestep .05','MaxSizeTimestep .1')
    def test_diagnostic_cap_cannot_leak(self):
        a='MaxSizeTimestep 1e-5\nCpuTimeBetRestartFile 3600'
        with self.assertRaises(ValueError):f.inputs_equal(a,a)
    def test_full_conservation_rejects_loss(self):
        r=f.v.prior.onset.mass_account([1.],[.9],[0.],1000);self.assertFalse(r['passes'])
    def test_full_step_envelope(self):
        with self.assertRaises(ValueError):f.v.prior.onset.mass_account([1.],[1.],[0.],32769)


if __name__=='__main__':unittest.main(verbosity=2)
