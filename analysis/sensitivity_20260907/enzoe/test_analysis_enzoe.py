import tempfile
from pathlib import Path
import unittest
import h5py
import numpy as np
from analyze_enzoe import independent_mass
class Tests(unittest.TestCase):
    def check_case(self,reported):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.h5'
            with h5py.File(p,'w') as h:
                g=h.create_group('B0');g.attrs['enzo_GridStartIndex']=[0,0,0];g.attrs['enzo_GridEndIndex']=[1,0,0];g.attrs['enzo_CellWidth']=[2.,1.,1.]
                g.create_dataset('field_density',data=np.array([[[1.,60.]]]))
            return independent_mass(dict(files=[str(p)],dense_mass=reported),dict(chi=100,dimensions=[2,1,1]))
    def test_per_cell_volume_and_threshold(self):self.assertEqual(self.check_case(120.),0)
    def test_wrong_mass_rejected(self):
        with self.assertRaises(ValueError):self.check_case(125.)
if __name__=='__main__':unittest.main()
