import tempfile
import unittest
from pathlib import Path
import numpy as np
import gasoline_controls as g

class Tests(unittest.TestCase):
    def test_layout(self):
        self.assertEqual(g.HEADER.itemsize,32)
        self.assertEqual(g.GAS.itemsize,48)

    def test_duplicate_parameter(self):
        with self.assertRaises(ValueError):g.params('nSteps=3\nnSteps=4')

    def test_comments(self):
        self.assertEqual(g.params('# header\nnSteps=3 # comment'),{'nSteps':'3'})

    def test_energy_factor(self):
        p=dict(bGasCooling='0',bGasAdiabatic='1',dGasConst=str(2/3),
               dConstGamma=str(5/3),dMeanMolWeight='1')
        self.assertAlmostEqual(g.energy_factor(p),1)
        p['dKpcUnit']='1'
        with self.assertRaises(ValueError):g.energy_factor(p)

    def test_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.json';g.write_new(p,{'x':1})
            with self.assertRaises(FileExistsError):g.write_new(p,{'x':2})

    def test_truncated_and_extra_payload(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data.std';p.write_bytes(b'x')
            with self.assertRaises(ValueError):g.read(p)
            h=np.zeros(1,g.HEADER);h['nsph']=h['nbodies']=1;h['ndim']=3
            p.write_bytes(h.tobytes()+bytes(47))
            with self.assertRaises(ValueError):g.read(p)
            p.write_bytes(h.tobytes()+bytes(49))
            with self.assertRaises(ValueError):g.read(p)

    def test_invalid_native_field(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data.std'
            h=np.zeros(1,g.HEADER);h['nsph']=h['nbodies']=1;h['ndim']=3
            a=np.zeros(1,g.GAS)
            p.write_bytes(h.tobytes()+a.tobytes())
            with self.assertRaises(ValueError):g.read(p)
            for k in ('mass','rho','temp','eps'):a[k]=1
            p.write_bytes(h.tobytes()+a.tobytes());self.assertEqual(g.read(p)[0],0)
            a['vel']=np.nan;p.write_bytes(h.tobytes()+a.tobytes())
            with self.assertRaises(ValueError):g.read(p)

if __name__=='__main__':unittest.main()
