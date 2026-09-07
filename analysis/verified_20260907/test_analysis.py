import math
import tempfile
import unittest
from pathlib import Path
from run_params import parse_file,find_params
from diagnostics_v2 import normalize


class AnalysisTests(unittest.TestCase):
    def test_flash_radius_and_fortran_exponent(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'flash.par'
            p.write_text('sim_rhoCloud=100\nsim_rhoAmbient=1\nsim_rCloud=1.0d-1\nsim_windVel=2.5\nsim_pAmbient=1\ngamma=1.6666666666666667\n')
            self.assertAlmostEqual(parse_file(p)['t_cc'],.4)

    def test_apk_units_and_density_ratio(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'athinput'
            p.write_text('<units>\ncode_length_cgs=10\ncode_mass_cgs=100\ncode_time_cgs=2\n<problem/cloud>\nrho_cloud_cgs=200\nrho_wind_cgs=2\nr0_cgs=50\nv_wind_cgs=25\n')
            got=parse_file(p)
            self.assertEqual(got['chi'],100)
            self.assertEqual(got['r_cloud'],5)
            self.assertEqual(got['v_wind'],5)
            self.assertEqual(got['t_cc'],10)

    def test_mass_loss_does_not_change_denominator(self):
        rows=[{'time_code':0,'t_over_tcc':0,'dense_mass':10,'total_mass_in_box':100},
              {'time_code':1,'t_over_tcc':1,'dense_mass':5,'total_mass_in_box':25}]
        # The broken formula gives (5/25)/(10/100)=2. The correct value is .5.
        self.assertEqual(normalize(rows)[1]['dense_mass_over_initial_dense_mass'],.5)

    def test_rejects_missing_initial_snapshot(self):
        with self.assertRaises(ValueError):
            normalize([{'time_code':1,'t_over_tcc':1,'dense_mass':5}])

    def test_rejects_duplicate_time(self):
        with self.assertRaises(ValueError):
            normalize([{'time_code':0,'t_over_tcc':0,'dense_mass':5}]*2)

    def test_missing_radius_not_assumed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'flash.par'
            p.write_text('sim_rhoCloud=100\nsim_rhoAmbient=1\nsim_windVel=2.5\n')
            self.assertIsNone(parse_file(p)['t_cc'])


if __name__=='__main__':
    unittest.main()
