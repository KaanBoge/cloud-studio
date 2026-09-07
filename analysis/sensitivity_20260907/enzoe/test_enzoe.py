import unittest
import run_enzoe as r
class Tests(unittest.TestCase):
    def test_only_velocity_energy_change(self):
        for l in (3,4,5):self.assertEqual(r.no_velocity(r.input_for(l,0)),r.no_velocity(r.input_for(l,1)))
    def test_invalid_cases_rejected(self):
        with self.assertRaises(ValueError):r.input_for(6,0)
        with self.assertRaises(ValueError):r.input_for(3,2)
    def test_dimensions_times_read_from_input(self):
        p=r.params_for(r.input_for(4,0));self.assertEqual(p['dimensions'],[128,64,64]);self.assertAlmostEqual(p['tmax']/p['t_cc'],5)
    def test_double_field_guard_includes_ghosts(self):
        self.assertGreater(r.budget(4),128*64*64*56*103)
    def test_cello_binary_subtraction_spacing(self):
        text=r.input_for(3,1)
        self.assertNotIn('1.0-0.5',text)
        self.assertIn('1.0 - 0.5',text)
if __name__=='__main__':unittest.main()
