import unittest
import numpy as np
from analyze import metrics,exact_pair_initial,volume


class Tests(unittest.TestCase):
    def test_mass_threshold_and_volume_weights(self):
        rho=np.array([[[[100.,20.]]]])
        data=dict(rho=rho,dv=np.array([[[[2.,3.]]]]),c=np.array([[[[0.,1.]]]]),
                  coord=[np.array([[[[1.,4.]]]])]*3,time=2.)
        got=metrics(data,dict(chi=100,rho_wind=1,r_cloud=1,t_cc=2),'athpp')
        self.assertEqual(got['dense_mass'],200.)
        self.assertEqual(got['tracer_mass'],60.)
        self.assertEqual(got['total_mass'],260.)
        self.assertEqual(got['dense_centroid_R'],1.)

    def test_changed_tracer_not_accepted_as_velocity_only(self):
        a=dict(rho=np.ones(2),c=np.ones(2))
        b=dict(rho=np.ones(2),c=np.zeros(2))
        with self.assertRaises(ValueError):exact_pair_initial(a,b)

    def test_volume_axes_and_every_cell(self):
        a=np.arange(8.).reshape(1,2,2,2)
        data=dict(rho=a,dims=[2,2,2],faces=[np.array([[0,1,2.]])]*3,
                  centers=[np.array([[.5,1.5]])]*3)
        np.testing.assert_array_equal(volume(data,'athpp'),a[0].transpose(2,1,0))
        np.testing.assert_array_equal(volume(data,'apk'),a[0].transpose(1,2,0))


if __name__=='__main__':unittest.main()
