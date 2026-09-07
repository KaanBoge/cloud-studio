from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from cooling_audit import inspect


class CoolingTests(unittest.TestCase):
    def test_retained_log_is_independent_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'athinput'
            p.write_text('<problem/cloud>\nT_wind_cgs = 6e-9\n<cooling>\nintegrator = townsend\ntable_filename = schure.cooling_1.0Z\n')
            r=inspect(p);self.assertEqual(r['status'],'requires_review')
            (Path(d)/'run.out').write_text('set but unused:\ncooling/integrator\ncooling/table_filename\n')
            r=inspect(p);self.assertEqual(r['status'],'cooling_not_enabled');self.assertEqual(len(r['issues']),4)

    def test_generator_refuses_before_overwriting_output(self):
        for extra,arg in [('', ['table.dat']), ('<cooling>\nintegrator = townsend\n',[])]:
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'template';p.write_text(extra);out=Path(d)/'input';out.write_text('PRESERVE')
                cmd=[sys.executable,str(Path(__file__).with_name('mkinput_legacy.py')),str(p),str(out),
                     '64','32','32','16','6','0.06','10','2.582']+arg
                r=subprocess.run(cmd,capture_output=True,text=True)
                self.assertNotEqual(r.returncode,0);self.assertIn('REFUSED',r.stderr)
                self.assertEqual(out.read_text(),'PRESERVE')

if __name__=='__main__':unittest.main()
