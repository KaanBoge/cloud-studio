import tempfile
import unittest
from pathlib import Path
import numpy as np
import mfv_l4_prepare as p
import mfv_l4_native_checks as v


class L4Tests(unittest.TestCase):
    def mount(self):return dict(target='/mnt/c',source='C:\\',fstype='9p',options='rw,noatime,aname=drvfs;path=C:\\;uid=1000')
    def test_mapping(self):p.mapping(self.mount(),dict(drive='C:'),2,1)
    def test_readonly_mount(self):
        m=self.mount();m['options']=m['options'].replace('rw,','ro,')
        with self.assertRaises(ValueError):p.mapping(m,dict(drive='C:'),2,1)
    def test_wrong_mount(self):
        m=self.mount();m['target']='/mnt/d'
        with self.assertRaises(ValueError):p.mapping(m,dict(drive='C:'),2,1)
    def test_wrong_drive(self):
        with self.assertRaises(ValueError):p.mapping(self.mount(),dict(drive='D:'),2,1)
    def test_same_device(self):
        with self.assertRaises(ValueError):p.mapping(self.mount(),dict(drive='C:'),1,1)
    def test_budget_exact(self):p.budget_gate(11*p.GIB,14*p.GIB,14*p.GIB,3*p.GIB)
    def test_guest_not_host_capacity(self):
        with self.assertRaises(ValueError):p.budget_gate(100*p.GIB,13*p.GIB,13*p.GIB,3*p.GIB)
    def test_host_not_guest_capacity(self):
        with self.assertRaises(ValueError):p.budget_gate(10*p.GIB,100*p.GIB,100*p.GIB,3*p.GIB)
    def test_missing_host_fails(self):
        with self.assertRaises(ValueError):p.budget_gate(20*p.GIB,20*p.GIB,None,1)
    def test_mounted_capacity_independent(self):
        with self.assertRaises(ValueError):p.budget_gate(20*p.GIB,12*p.GIB,20*p.GIB,3*p.GIB)
    def test_existing_target(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):p.new_target(Path(d))
    def test_stale_pid(self):
        with self.assertRaises(ValueError):p.ownership(12,1.,2.,12)
    def test_wrong_pgid(self):
        with self.assertRaises(ValueError):p.ownership(12,1.,1.,13)
    def test_l3_ids_rejected(self):
        with self.assertRaises(ValueError):v.validate_arrays(dict(ParticleIDs=np.arange(1,65537)),False)
    def test_bad_law_rejected(self):
        with self.assertRaises(ValueError):v.ic_law({}, {}, 2)
    def test_missing_native_fields(self):
        with self.assertRaises(ValueError):v.validate_arrays(dict(ParticleIDs=np.arange(1,v.N+1,dtype=np.uint32)))
    def test_wrong_native_dtype(self):
        a={k:np.ones((v.N,3) if k in ('Coordinates','Velocities','ParticleVelocities') else (v.N,),dtype=dt) for k,dt in v.FIELDS.items()}
        a['ParticleIDs']=np.arange(1,v.N+1,dtype=np.uint32);a['Density']=a['Density'].astype(np.float64)
        with self.assertRaises(ValueError):v.validate_arrays(a)
    def test_l4_rank_prefix_can_exceed_l3_count(self):
        a,_=v.take(bytes(70000*4),0,'<i4',70000);self.assertEqual(len(a),70000)
    def test_truncated_rank_prefix(self):
        with self.assertRaises(ValueError):v.take(bytes(4),0,'<i4',2)
    def test_wrong_clock_abi(self):
        with self.assertRaises(ValueError):v.clock_abi({'global_data_all_processes':np.dtype([('Ti_Current','<i4')])})
    def test_nonvelocity_change(self):
        with self.assertRaises(ValueError):v.prior.same_fields({'Masses':np.array([1])},{'Masses':np.array([2])})
    def test_failed_mass_account(self):
        r=v.mass_account([1.],[2.],[0.],1);self.assertFalse(r['passes'])
    def test_production_step_is_not_timing_cap(self):
        text=(p.BASE/'params_mfv_L4.txt').read_text();physics={'t_cc':3.872983346207417}
        self.assertEqual(float(p.input_values(text,physics,'full')['MaxSizeTimestep']),.05)
        with self.assertRaises(ValueError):p.input_values(text.replace('0.05','0.00001'),physics,'full')


if __name__=='__main__':unittest.main(verbosity=2)
