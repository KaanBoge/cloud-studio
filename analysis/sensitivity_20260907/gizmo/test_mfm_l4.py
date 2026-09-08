import tempfile,unittest
from pathlib import Path
import numpy as np
import mfm_l4_controls as m

class L4SafetyTests(unittest.TestCase):
    def test_original_full_numerics_unchanged(self):
        old=m.params((m.ROOT/'params_mfm_L4.txt').read_text());new=m.input_values('full')
        changed={k for k in old if old[k]!=new[k]}
        self.assertEqual(changed,{'TimeMax','TimeBetSnapshot'})
        self.assertEqual(float(new['MaxSizeTimestep']),.05)
        self.assertEqual(float(new['MaxMemSize']),1500)
        self.assertEqual(float(new['TimeMax']),5*m.physics()['t_cc'])
    def test_tiny_cap_never_used_in_full_run(self):
        for role,cap in [('full',1e-5),('smoke',1e-5),('timing',None),('timing',1e-6)]:
            with self.assertRaises(ValueError):m.input_values(role,cap)
        self.assertEqual(float(m.input_values('timing',5e-6)['MaxSizeTimestep']),5e-6)
    def test_exact_nonvelocity_allows_only_velocity_difference(self):
        a={'Masses':np.array([1.]),'Velocities':np.array([[0.,0.,0.]])}
        b={'Masses':np.array([1.]),'Velocities':np.array([[2.,0.,0.]])}
        m.exact_nonvelocity(a,b)
        b['Masses'][0]=2
        with self.assertRaises(ValueError):m.exact_nonvelocity(a,b)
    def test_wrong_schema_rejected(self):
        with self.assertRaises(ValueError):m.exact_nonvelocity({'a':np.array([1])},{'b':np.array([1])})
    def test_existing_run_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):m.prepare(Path(tmp),0,'full',1)
    def test_invalid_mode_refused(self):
        with self.assertRaises(ValueError):m.prepare(Path('/not-used'),2,'full',1)
    def test_l3_timing_evidence_refused(self):
        with self.assertRaises(ValueError):m.timing_proof({'level':3,'variant':'mfm'},{'status':'passed'})
    def test_l3_budget_refused(self):
        cases=[{'mode':i,'level':3,'variant':'mfm','role':'smoke'} for i in (0,1)]
        with self.assertRaises(ValueError):m.measured_budget(cases)
    def test_original_dependencies_unchanged(self):
        self.assertFalse(m.dependencies(False)['compiled_anything'])
        self.assertEqual(m.NATIVE_COUNT,524288)

if __name__=='__main__':unittest.main()
