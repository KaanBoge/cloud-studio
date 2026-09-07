import tempfile
from pathlib import Path
import unittest
import numpy as np
import run_ramses as r

class Controls(unittest.TestCase):
    def test_only_mode_differs(self):
        for level in (3,4,5):
            self.assertEqual(r.no_mode(r.input_for(level,0)),r.no_mode(r.input_for(level,1)))
    def test_invalid_mode_or_level(self):
        for level,mode in ((2,0),(6,1),(3,2)):
            with self.assertRaises(ValueError):r.input_for(level,mode)
    def test_reads_matched_parameters(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'run.nml';p.write_text(r.input_for(4,1));values=r.parameters(p)
            self.assertEqual(values['dimensions'],[128,64,64]);self.assertEqual(values['velocity_ic'],1)
            self.assertAlmostEqual(values['mach'],2);self.assertAlmostEqual(values['tmax']/values['t_cc'],5)
    def test_missing_parameter_rejected(self):
        with self.assertRaises(ValueError):r.replace_scalar('tend=1','levelmin',5)
    def test_duplicate_mode_rejected(self):
        with self.assertRaises(ValueError):r.no_mode('velocity_ic = 0\nvelocity_ic = 1')
    def test_analytic_check_discriminates(self):
        p=dict(x_cloud=3,y_cloud=5,z_cloud=5,r_cloud=1,edge=.1,rho_wind=1,chi=100,v_wind=2.582,rv_scale=1.3,p_wind=1)
        radius=np.array([0.,1.,1.3,1.35,2.]);f=.5*(1-np.tanh((radius-1)/.1))
        d=dict(time=0,xyz=np.column_stack((3+radius,np.full(5,5),np.full(5,5))),rho=1+99*f,
               vel=np.column_stack((np.where(radius>1.3,2.582,0),np.zeros((5,2)))),pressure=np.ones(5),tracer_concentration=f)
        # Avoid ambiguous rounding of the synthetic exact boundary coordinate.
        d['xyz'][2,0]=4.299999999999
        r.check_initial(d,p,0)
        with self.assertRaises(ValueError):r.check_initial(d,p,1)
    def test_grid_coverage(self):
        p=dict(dimensions=[2,1,1],boxlen=20,gamma=5/3)
        meta=dict(nvar=6,ncpu=8,gamma=5/3,domain_width=[20,10,10])
        c=np.ones((2,10));c[:,:3]=[[15,5,5],[5,5,5]];c[:,3]=10
        ordered=r.ordered_grid(meta,c,p)
        self.assertEqual(ordered[0,0],5)
        c[1,:3]=c[0,:3]
        with self.assertRaises(ValueError):r.ordered_grid(meta,c,p)
    def test_missing_cell_and_nonfinite_rejected(self):
        p=dict(dimensions=[2,1,1],boxlen=20,gamma=5/3)
        meta=dict(nvar=6,ncpu=8,gamma=5/3,domain_width=[20,10,10])
        c=np.ones((2,10));c[:,:3]=[[5,5,5],[15,5,5]];c[:,3]=10
        with self.assertRaises(ValueError):r.ordered_grid(meta,c[:1],p)
        c[0,9]=np.inf
        with self.assertRaises(ValueError):r.ordered_grid(meta,c,p)

if __name__=='__main__':unittest.main()
