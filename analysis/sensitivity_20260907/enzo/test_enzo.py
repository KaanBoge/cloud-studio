import unittest
import run_enzo as r
class Tests(unittest.TestCase):
    def test_pair_only_mode_changes(self):
        for level in (3,4,5):self.assertEqual(r.no_mode(r.input_for(level,0)),r.no_mode(r.input_for(level,1)))
    def test_modes_and_levels_rejected(self):
        for level,mode in ((2,0),(5,2)):
            with self.assertRaises(ValueError):r.input_for(level,mode)
    def test_full_double_precision_storage_budget(self):
        self.assertGreater(r.budget(5)/r.GIB,30)
    def test_duplicate_switch_rejected(self):
        with self.assertRaises(ValueError):r.no_mode('CloudWindVelocityIC = 0\nCloudWindVelocityIC = 1')
    def test_wallclock_restart_exit_disabled(self):
        for level in (3,4,5):self.assertIn('dtRestartDump = -99999',r.input_for(level,0))
if __name__=='__main__':unittest.main()
