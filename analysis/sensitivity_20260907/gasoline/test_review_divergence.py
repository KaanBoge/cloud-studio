"""Synthetic selected-ABI/identity/roundtrip tests; never execute a solver."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np
import review_divergence as r


class ReviewTests(unittest.TestCase):
    def test_identity_mapping(self):
        self.assertEqual(r.order([2,0,1],3).tolist(),[1,2,0])
        for bad in ([0,0,2],[0,1],[0,.5,2],[0,1,np.nan]):
            with self.assertRaises(ValueError): r.order(bad,3)

    def test_two_spacing_detection(self):
        a=np.array([1.],dtype=np.float32)
        b=np.nextafter(np.nextafter(a,np.float32(2)),np.float32(2))
        d=r.difference(a,b,1.)
        self.assertEqual(d['max_declared_spacing_ratio'],2.)
        self.assertEqual(d['exceeding_particle_ids'],[0])

    def test_vector_component_and_signed_zero(self):
        d=r.difference([[1.,2.,-0.]],[[1.,3.,0.]])
        self.assertEqual(d['unequal_components'],1)
        self.assertEqual(d['largest_difference']['component'],1)
        self.assertEqual(d['signed_zero_components'],1)

    def test_nonfinite_and_shape(self):
        with self.assertRaises(ValueError):r.difference([np.nan],[1.])
        with self.assertRaises(ValueError):r.difference([1.],[[1.]])

    def make_checkpoint(self,path):
        with path.open('wb') as f:
            f.write(b'header')
            for i in (1,0,2):
                f.write(struct.pack('<ii9d',i,4,2.,.3,1.+i,2.,3.,4.,5.,6.,7.))
                # Deliberately arbitrary tail, not physical fields in this decoder.
                f.write(bytes([255])*40)

    def test_checkpoint_prefix_and_independent_decoder(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.chk';self.make_checkpoint(p)
            a=r.prefix(p,6,3)
            self.assertEqual(a['id'].tolist(),[0,1,2])
            self.assertEqual(a['pos'][:,0].tolist(),[1,2,3])
            self.assertEqual(a['u'].tolist(),[7,7,7])

    def test_checkpoint_truncation_and_nonfinite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.chk';self.make_checkpoint(p)
            with self.assertRaises(ValueError):r.prefix(p,7,3)
            with p.open('r+b') as f:
                f.seek(6+72);f.write(struct.pack('<d',float('nan')))
            with self.assertRaises(ValueError):r.prefix(p,6,3)

    def test_checkpoint_export_factor(self):
        cp=np.zeros(2,dtype=r.CHECK);raw=np.zeros(2,dtype=r.GAS)
        for name in ('mass','eps','pos','vel','u'): cp[name]=1.234567891
        for name in ('mass','eps','pos','vel'):raw[name]=cp[name]
        raw['temp']=cp['u']*2.5
        self.assertTrue(all(r.check_export(cp,raw,2.5).values()))
        with self.assertRaises(ValueError):r.check_export(cp,raw,1.)

    def test_temperature_and_duplicate_params(self):
        p=dict(bGasCooling='0',bGasAdiabatic='1',bComove='0',
               dConstGamma='1.5',dMeanMolWeight='2',dGasConst='4')
        self.assertEqual(r.temperature_factor(p),.25)
        with self.assertRaises(ValueError):r.temperature_factor(dict(p,bGasCooling='1'))
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'input';path.write_text('a=1\na=2\n')
            with self.assertRaises(ValueError):r.params(path)

    def test_write_and_hash_guard(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'report.json';r.write_new(path,dict(preserved=True))
            before=r.sha(path)
            with self.assertRaises(FileExistsError):r.write_new(path,{})
            self.assertEqual(r.checked_hash(path,before),before)
            with self.assertRaises(ValueError):r.checked_hash(path,'0'*64)

    def test_tipsy_schema_and_id_order(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'state'
            data=np.ones(2,dtype=r.GAS);data['rho']=[4,5]
            with path.open('wb') as f:
                f.write(r.HEADER.pack(.2,2,3,2,0,0,0));f.write(data.tobytes())
            Path(str(path)+'.iord').write_text('2\n1\n0\n')
            t,a=r.tipsy(path)
            self.assertEqual(t,.2);self.assertEqual(a['rho'].tolist(),[5,4])
            with path.open('ab') as f:f.write(b'x')
            with self.assertRaises(ValueError):r.tipsy(path)


if __name__ == '__main__':
    unittest.main()
