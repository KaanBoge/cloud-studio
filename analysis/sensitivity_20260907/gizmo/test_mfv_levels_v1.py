"""New scalar-analysis tests only; do not launch native experiments."""
import copy
import unittest
import analyze_mfv_levels_v1 as a


def rows(mass=(10.,8.,5.)):
    return [dict(time_code=t,dense_mass=m) for t,m in zip((0.,2.5,5.),mass)]


def cases():
    physics=dict(chi=100,mach=2,ranks=8,t_cc=1.)
    ans=[]
    for law in ('sharp13','tanh13'):
        series=[dict(r,path=str(i),elements=524288,t_over_tcc=r['time_code'],total_mass=20.,min_energy=1.,independent_relative_errors=[0.,0.]) for i,r in enumerate(rows())]
        ans.append(dict(law=law,status='passed_full_native_checks',physics=physics,binary_sha256=a.BINARY_SHA,input_sha256='same',rows=series,
                        resources=dict(returncode=0,error=None,wall_seconds=1),cadence=dict(bits=60,actual_count=3,expected_count=3,maximum_offset=0.,tolerance_code=1e-14),
                        terminal=dict(mass_account=dict(passes=True,response_detected=True,residual=0.,allowance=1e-10))))
    return ans,physics


class TestMFVLevels(unittest.TestCase):
    def test_identical(self):
        self.assertEqual(a.metrics(rows(),rows(),1)['peak_curve_difference_over_initial_mass'],0)
    def test_fixed_denominator(self):
        self.assertAlmostEqual(a.metrics(rows(),rows((10,6,3)),1)['peak_curve_difference_over_initial_mass'],.2)
    def test_changed_initial(self):
        with self.assertRaises(ValueError):a.metrics(rows(),rows((11,8,5)),1)
    def test_zero_initial(self):
        with self.assertRaises(ValueError):a.curve(rows((0,0,0)),1)
    def test_nonfinite(self):
        with self.assertRaises(ValueError):a.curve(rows((10,float('nan'),5)),1)
    def test_duplicate_time(self):
        r=rows();r[1]['time_code']=0
        with self.assertRaises(ValueError):a.curve(r,1)
    def test_incomplete(self):
        with self.assertRaises(ValueError):a.curve(rows()[:-1],1)
    def test_no_extrapolation(self):
        with self.assertRaises(ValueError):a.scalar_interp([0,5],[1,0],6)
        self.assertEqual(a.scalar_interp([0,5],[1,0],2.5),.5)
    def test_valid_metadata(self):
        c,p=cases();self.assertEqual(a.validate_l4(c,p)['peak_curve_difference_over_initial_mass'],0)
    def test_law_order(self):
        c,p=cases()
        with self.assertRaises(ValueError):a.validate_l4(c[::-1],p)
    def test_native_recipe(self):
        for key,value in [('binary_sha256','wrong'),('input_sha256','different'),('status','failed')]:
            c,p=cases();c[0][key]=value
            with self.assertRaises(ValueError):a.validate_l4(c,p)
    def test_bad_cadence(self):
        for key,value in [('bits',29),('actual_count',2),('maximum_offset',1.)]:
            c,p=cases();c[0]['cadence'][key]=value
            with self.assertRaises(ValueError):a.validate_l4(c,p)
    def test_field_evidence(self):
        for key,value in [('elements',65536),('min_energy',0),('independent_relative_errors',[0,.1]),('t_over_tcc',9)]:
            c,p=cases();c[0]['rows'][1][key]=value
            with self.assertRaises(ValueError):a.validate_l4(c,p)
    def test_failed_conservation(self):
        c,p=cases();c[0]['terminal']['mass_account']['passes']=False
        with self.assertRaises(ValueError):a.validate_l4(c,p)


if __name__=='__main__':unittest.main()
