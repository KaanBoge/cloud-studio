import json
from pathlib import Path
import tempfile
import unittest
import serial_observer_run as s


class ObserverTests(unittest.TestCase):
    def good(self):
        rows=[dict(stage=stage,count=32768,bytes=32768*408,equal=True) for stage in
              ('master_written','remote_written','master_restored')]
        return rows

    def log(self,rows):
        return '\n'.join('CLOUD_SERIAL_OBSERVER '+json.dumps(row) for row in rows)+'\nCLOUD_INITIAL_NATIVE_OUTPUT time=0 file=state.initial\n'

    def test_markers_pass(self):
        self.assertEqual(s.records(self.log(self.good())),self.good())

    def test_population_and_failure(self):
        for rows in (self.good()[:2],self.good()+self.good()[:1],list(reversed(self.good()))):
            with self.assertRaises(ValueError):s.records(self.log(rows))
        rows=self.good();rows[1]['equal']=False
        with self.assertRaises(ValueError):s.records(self.log(rows))
        rows=self.good();rows[1]['count']=1
        with self.assertRaises(ValueError):s.records(self.log(rows))

    def test_input_only_duration_changes(self):
        p=dict(nSteps='120',iOutInterval='6',iCheckInterval='60',bGasAdiabatic='1',
               bGasCooling='0',dExtraStore='0.2',dDelta='0.03227486122')
        text=''.join(k+' = '+v+'\n' for k,v in p.items())
        got=s.parameters(s.input_six(text));wanted=dict(p,nSteps='6')
        self.assertEqual(got,wanted)
        with self.assertRaises(ValueError):s.input_six(text.replace('120','60'))
        with self.assertRaises(ValueError):s.parameters('x=1\nx=2')

    def test_exclusive_result(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'result.json';s.save(p,dict(original=True));h=s.sha(p)
            with self.assertRaises(FileExistsError):s.save(p,{})
            self.assertEqual(s.sha(p),h)


if __name__=='__main__':unittest.main()
