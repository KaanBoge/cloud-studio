import tempfile
import unittest
from pathlib import Path
import h5py
import numpy as np
import run_l4 as q


class BatchTests(unittest.TestCase):
    def test_profiles_are_pinned_and_blocks_divide_l4(self):
        for code, chi in q.PLAN:
            p = q.profile_for(code)
            q.r.check_proof(p, chi)
            self.assertEqual(p['level'], 4)
            text = q.r.input_for(code, 4, chi, p['block'])
            self.assertNotIn('<cooling>', text)
            self.assertNotIn('galilean_shift = true', text)
            self.assertIn('rv_scale = 1.3', text)
            self.assertIn('nlim = -1', text)

    def write(self, directory, code, times, bad=False):
        for i,t in enumerate(times):
            with h5py.File(Path(directory)/f'{i:05}.{"athdf" if code=="athpp" else "phdf"}', 'w') as f:
                if code == 'athpp':
                    f.attrs['Time'] = t
                    f.attrs['VariableNames'] = [b'rho',b'press',b'vel1',b'vel2',b'vel3',b'r0']
                    data=np.ones((6,1,1,1,1))
                else:
                    f.create_group('Info').attrs['Time'] = t
                    data=np.ones((1,6,1,1,1))
                if bad: data.flat[0] = np.nan
                f['prim'] = data

    def test_actual_time_offsets_reported_not_relabelled(self):
        for code in ('athpp','apk'):
            with tempfile.TemporaryDirectory() as tmp:
                times=np.linspace(0,5,101); times[1:-1]+=.01
                self.write(tmp,code,times)
                got=q.validate_fields(Path(tmp),code,1)
                self.assertTrue(got['complete_outputs'])
                self.assertFalse(got['exact_nominal_times'])
                self.assertAlmostEqual(got['max_time_offset_tcc'],.01)

    def test_missing_repeated_and_nonfinite_outputs_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp,'athpp',[0,1,1,5])
            got=q.validate_fields(Path(tmp),'athpp',1)
            self.assertFalse(got['complete_outputs'])
            self.assertEqual(got['unique_snapshots'],3)
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp,'apk',[0],bad=True)
            with self.assertRaisesRegex(ValueError,'Nonfinite'):
                q.validate_fields(Path(tmp),'apk',1)

    def test_storage_still_reserves_all_frames_and_safety(self):
        disk,_=q.r.budgets(q.profile_for('apk'))
        self.assertGreater(disk,48*128*64*64*101)
        with self.assertRaises(RuntimeError):
            q.r.require_storage({'effective_free_bytes':disk,'windows_backing_volume':None},disk)


if __name__=='__main__': unittest.main()
