import tempfile
from pathlib import Path
import unittest
import numpy as np
import run_flashx as f

class FlashControls(unittest.TestCase):
    def test_only_velocity_parameter_differs(self):
        for level in (3,4,5):self.assertEqual(f.no_mode(f.input_for(level,0)),f.no_mode(f.input_for(level,1)))
    def test_invalid_case_rejected(self):
        for level,mode in ((2,0),(6,0),(3,2)):
            with self.assertRaises(ValueError):f.input_for(level,mode)
    def test_native_radius_and_level_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'flash.par';p.write_text(f.input_for(4,0));v=f.parameters(p)
            self.assertEqual(v['dimensions'],[128,64,64]);self.assertEqual(v['r_cloud'],1)
            self.assertEqual(v['domain_left'],[-3,-5,-5]);self.assertEqual(v['domain_right'],[17,5,5])
            self.assertAlmostEqual(v['mach'],2);self.assertAlmostEqual(v['tmax']/v['t_cc'],5)
    def test_full_checkpoint_cadence_and_no_overwriting(self):
        text=f.input_for(4,0)
        self.assertIn('rolling_checkpoint = 10000',text)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'flash.par';p.write_text(text);_,v,_=f.read_values(p)
            self.assertEqual(v['checkpointfileintervaltime'],v['plotfileintervaltime'])
    def test_mode_discriminates(self):
        p=dict(sim_xctr=0,sim_yctr=0,sim_zctr=0,sim_smoothwidth=.1,r_cloud=.1,rho_wind=1,chi=100,rv_scale=1.3,v_wind=2.582,p_wind=1)
        radius=np.array([0,.1,.12,.135,.2]);frac=.5*(1-np.tanh((radius-.1)/.01))
        d=dict(time=0,xyz=np.column_stack((radius,np.zeros((5,2)))),rho=1+99*frac,pressure=np.ones(5),
            vel=np.column_stack((np.where(radius>.13,2.582,0),np.zeros((5,2)))))
        f.check_initial(d,p,0)
        with self.assertRaises(ValueError):f.check_initial(d,p,1)
    def test_recovery_roundoff_but_not_real_pressure_change(self):
        a={k:np.ones(3) for k in f.CHECK_FIELDS};b={k:v.copy() for k,v in a.items()}
        b['temp']+=1e-15;f.pair_field_checks(a,b)
        b['pres']+=1e-5
        with self.assertRaises(ValueError):f.pair_field_checks(a,b)
    def test_density_change_rejected(self):
        a={k:np.ones(3) for k in f.CHECK_FIELDS};b={k:v.copy() for k,v in a.items()};b['dens'][0]+=1e-14
        with self.assertRaises(ValueError):f.pair_field_checks(a,b)

if __name__=='__main__':unittest.main()
