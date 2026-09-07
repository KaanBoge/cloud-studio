"""Regression tests for the prepare/run guards and native-time accounting."""
import contextlib
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import h5py
import numpy as np
import run_optimized as r

class LauncherTests(unittest.TestCase):
    def test_all_twelve_input_combinations(self):
        profiles=json.loads((r.HERE/'optimized_profiles.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            for code in ('athpp','apk'):
                for level in (5,6):
                    profile=profiles[f'{code}_L{level}']
                    for chi in (10,100,1000):
                        r.check_proof(profile,chi)
                        text=r.input_for(code,level,chi,profile['block'])
                        f=Path(tmp)/'athinput';f.write_text(text)
                        p=r.parse_file(f)
                        self.assertAlmostEqual(p['chi'],chi)
                        self.assertAlmostEqual(p['mach'],2)
                        self.assertAlmostEqual(p['tmax']/p['t_cc'],5)
                        self.assertAlmostEqual(p['output_dt']/p['t_cc'],.05)
                        self.assertEqual(p['rv_scale'],1.3)
                        self.assertIn('nlim = -1',text)
                        self.assertIn('hdf5',text)
                        self.assertIn('rst',text)
                        self.assertNotIn('2D',text)
                        self.assertNotIn('tanh-smoothed',text)

    def test_mpi_uses_all_sixteen_threads_only_for_cpu(self):
        profiles=json.loads((r.HERE/'optimized_profiles.json').read_text())
        self.assertIn('--use-hwthread-cpus',r.mpi_command(profiles['athpp_L6']))
        self.assertNotIn('--use-hwthread-cpus',r.mpi_command(profiles['apk_L6']))

    def test_modified_binary_is_rejected(self):
        p=json.loads((r.HERE/'optimized_profiles.json').read_text())['athpp_L5']
        p['binary_sha256']='wrong'
        with self.assertRaises(ValueError):r.check_proof(p,10)

    def test_disk_budget_does_not_assume_early_time_compression(self):
        p=json.loads((r.HERE/'optimized_profiles.json').read_text())['apk_L6']
        p['measured_native_output_bytes_per_cell']=1
        disk,_=r.budgets(p)
        self.assertGreater(disk,48*33554432*101)

    def prepared(self,tmp):
        p=json.loads((r.HERE/'optimized_profiles.json').read_text())['athpp_L5']
        t=Path(tmp);text=r.input_for('athpp',5,10,p['block'])
        (t/'athinput').write_text(text)
        record={'status':'prepared','parameter_sha256':r.sha(t/'athinput'),
                'binary_sha256':p['binary_sha256'],'command':r.mpi_command(p)}
        (t/'provenance.json').write_text(json.dumps(record))
        return t,text,p

    def test_prepared_can_be_reopened(self):
        with tempfile.TemporaryDirectory() as tmp:
            t,text,p=self.prepared(tmp)
            self.assertEqual(r.validate_prepared(t,text,p)['status'],'prepared')

    def test_existing_output_prevents_reexecution(self):
        with tempfile.TemporaryDirectory() as tmp:
            t,text,p=self.prepared(tmp);(t/'run.log').write_text('existing run')
            with self.assertRaises(ValueError):r.validate_prepared(t,text,p)

    def test_changed_input_prevents_reexecution(self):
        with tempfile.TemporaryDirectory() as tmp:
            t,text,p=self.prepared(tmp);(t/'athinput').write_text(text+'\n# changed')
            with self.assertRaises(ValueError):r.validate_prepared(t,text,p)

    def write_times(self,tmp,times):
        for i,t in enumerate(times):
            with h5py.File(Path(tmp)/f'{i:04}.athdf','w') as f:f.attrs['Time']=float(t)

    def test_exact_101_times(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_times(tmp,np.linspace(0,5,101))
            self.assertTrue(r.inspect_cadence(Path(tmp),'athpp',1)['cadence_passed'])

    def test_missing_and_beyond_end_frames_do_not_pass(self):
        for times in (np.linspace(0,5,100),list(np.linspace(0,5,101))+[5.1]):
            with tempfile.TemporaryDirectory() as tmp:
                self.write_times(tmp,times)
                self.assertFalse(r.inspect_cadence(Path(tmp),'athpp',1)['cadence_passed'])

    def test_duplicate_terminal_retained_not_counted_as_new_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_times(tmp,list(np.linspace(0,5,101))+[5])
            got=r.inspect_cadence(Path(tmp),'athpp',1)
            self.assertTrue(got['cadence_passed'])
            self.assertEqual(len(got['native_time_rows']),102)
            self.assertEqual(len(list(Path(tmp).glob('*.athdf'))),102)

if __name__=='__main__':unittest.main()
