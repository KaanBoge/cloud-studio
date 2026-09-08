import json,unittest
import numpy as np
from gadget_l4_controls import input_values,initial_checks,paired_nonvelocity,COUNT,DX,ROOT
from gadget_controls import parameters,metadata
from native_cadence import expected_times,cadence

class L4Tests(unittest.TestCase):
    def setUp(self):self.text=(ROOT/'params_L4.txt').read_text();self.p=metadata()
    def example(self):
        ic={'ParticleIDs':np.array([1],dtype=np.uint64),'Coordinates':np.array([[DX/2,DX/2,DX/2]]),
            'Masses':np.array([DX**3]),'InternalEnergy':np.array([1.5]),'Velocities':np.array([[self.p['v_wind'],0,0]])}
        a={k:v.astype(np.uint32 if k=='ParticleIDs' else np.float32) for k,v in ic.items()}
        a.update(Density=np.array([1],np.float32),Pressure=np.array([1],np.float32));return a,ic
    def test_l4_sampling_not_l3(self):self.assertEqual(COUNT,524288);self.assertEqual(DX,.15625)
    def test_per_level_initial_pressure(self):
        a,ic=self.example();r=initial_checks(a,ic,self.p);self.assertEqual(r['native_density_vs_lattice_max_relative'],0);json.dumps(r,allow_nan=False)
    def test_velocity_error_rejected(self):
        a,ic=self.example();a['Velocities'][0,0]+=.01
        with self.assertRaises(ValueError):initial_checks(a,ic,self.p)
    def test_pair_density_error_rejected(self):
        a,ic=self.example();b={k:v.copy() for k,v in a.items()};b['Density'][0]=2
        with self.assertRaises(ValueError):paired_nonvelocity(a,b)
    def test_original_numerics_preserved(self):
        original=parameters(self.text);v=input_values(self.text,self.p)
        changed={k for k in original if v[k]!=original[k]}
        self.assertEqual(changed,{'InitCondFile','TimeMax','TimeBetSnapshot','TimeBetStatistics'})
        self.assertEqual(v['MaxMemSize'],'2000');self.assertEqual(v['CpuTimeBetRestartFile'],'7200')
    def test_l3_input_rejected(self):
        with self.assertRaises(ValueError):input_values((ROOT/'params_L3.txt').read_text(),self.p)
    def test_numerical_change_rejected(self):
        with self.assertRaises(ValueError):input_values(self.text.replace('0.050000000','0.04'),self.p)
    def test_short_schedule(self):
        v=input_values(self.text,self.p,short=True);times,_,_=expected_times(v);np.testing.assert_array_equal(times,[0,.1])
    def test_full_native_schedule_unchanged(self):
        v=input_values(self.text,self.p);times,_,_=expected_times(v);proof=cadence(times,self.p,v);self.assertEqual(proof['native_snapshots'],101)

if __name__=='__main__':unittest.main()
