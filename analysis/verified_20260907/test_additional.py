import json
import math
from pathlib import Path
import tempfile
import unittest
from run_params import parse_file,read_values
from run_corrected_athpp import make_input
from figure2_v2 import load_runs


class AdditionalTests(unittest.TestCase):
    def test_every_ladder_input(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'athinput'
            for level in range(1,7):
                for chi in (10,100,1000):
                    p.write_text(make_input(level,chi))
                    got=parse_file(p);raw,v,s=read_values(p)
                    nx=8*2**level
                    self.assertEqual([int(s['mesh',f'nx{i}']) for i in (1,2,3)],[nx,nx//2,nx//2])
                    self.assertAlmostEqual(got['output_dt']/got['t_cc'],.05)
                    self.assertAlmostEqual(got['tmax']/got['t_cc'],5)
                    self.assertEqual(got['rv_scale'],1.3)
    def test_no_legacy_fraction_plot(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'old.json';p.write_text(json.dumps({'series':[{'t':0,'mass_frac':.1}]}))
            with self.assertRaises(ValueError): load_runs([p])
    def test_apk_pressure_from_parameters(self):
        p=Path('/home/kaan/ic_audit_20260907/grid_tests/apk_chi10/athinput')
        if not p.exists(): self.skipTest('Local native input not available')
        got=parse_file(p)
        self.assertAlmostEqual(got['p_wind'],1,places=12)
        self.assertAlmostEqual(got['mach'],2,places=12)
    def test_missing_apk_radius_serializes_as_null(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'athinput'
            p.write_text('rho_cloud_cgs=10\nrho_wind_cgs=1\ncode_length_cgs=1\ncode_mass_cgs=1\ncode_time_cgs=1\n')
            got=parse_file(p)
            self.assertIsNone(got['r_cloud'])
            json.dumps(got,allow_nan=False)


if __name__=='__main__': unittest.main()
