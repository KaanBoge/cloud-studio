import unittest
import numpy as np
from gadget_controls import law,parameters,smoke_inputs

class GadgetTests(unittest.TestCase):
    def setUp(self):self.p=dict(v_wind=2.0,rv_scale=1.3,r_cloud=1,density_width=.1)
    def test_sharp_boundary(self):np.testing.assert_array_equal(law(np.array([1,1.3,1.4]),0,self.p),[0,0,2])
    def test_historical_center(self):self.assertEqual(law(np.array([1.3]),1,self.p)[0],1)
    def test_invalid_mode(self):
        with self.assertRaises(ValueError):law(np.array([1.3]),2,self.p)
    def test_duplicate_input_rejected(self):
        with self.assertRaises(ValueError):parameters('TimeMax 1\nTimeMax 2')
    def test_comments_not_parameters(self):self.assertEqual(parameters('% comment\nTimeMax 1 # comment'),{'TimeMax':'1'})
    def test_no_numerical_change(self):
        text='MaxSizeTimestep 0.050000000\nCourantFac 0.15\nDesNumNgb 64\nMinEgySpec 0\nMaxMemSize 1000\nCpuTimeBetRestartFile 7200'
        result=smoke_inputs(text)
        for key,value in parameters(text).items():self.assertEqual(result[key],value)
        self.assertEqual(result['TimeMax'],'0.1')
    def test_changed_timestep_rejected(self):
        text='MaxSizeTimestep 0.00001\nCourantFac 0.15\nDesNumNgb 64\nMinEgySpec 0\nMaxMemSize 1000'
        with self.assertRaises(ValueError):smoke_inputs(text)

if __name__=='__main__':unittest.main()
