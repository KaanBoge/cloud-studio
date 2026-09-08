import unittest
from pathlib import Path
import runner as r


class Gates(unittest.TestCase):
    def test_path_exact(self):
        r.verify_path()
        with self.assertRaises(ValueError):r.verify_path(Path('/mnt/c/Users/kaanb/Downloads'))

    def test_mount(self):
        good=dict(target='/mnt/c',source='C:\\',fstype='9p',options='rw,aname=drvfs;path=C:\\;uid=1000')
        r.mapping_gate(good,dict(drive='C:'),1,2)
        for field,value in (('target','/mnt/d'),('source','D:\\'),('fstype','ext4'),('options','ro')):
            with self.assertRaises(ValueError):r.mapping_gate(dict(good,**{field:value}),dict(drive='C:'),1,2)
        with self.assertRaises(ValueError):r.mapping_gate(good,dict(drive='D:'),1,2)
        with self.assertRaises(ValueError):r.mapping_gate(good,dict(drive='C:'),2,2)

    def test_budgets(self):
        reserve=r.RESERVE+r.ANCILLARY;payload=70*r.GIB
        r.budget_gate(reserve,reserve+payload,reserve+payload,payload)
        for values in ((reserve-1,10**15,10**15,payload),(reserve,reserve+payload-1,10**15,payload),
                       (reserve,10**15,reserve+payload-1,payload),(-1,10**15,10**15,payload),
                       (float(reserve),10**15,10**15,payload)):
            with self.assertRaises(ValueError):r.budget_gate(*values)

    def test_live_separate_reserves(self):
        r.budget_gate(r.RESERVE,r.RESERVE,r.RESERVE,0,True)
        for low in range(3):
            values=[r.RESERVE]*3;values[low]-=1
            with self.assertRaises(ValueError):r.budget_gate(*values,0,True)

    def test_l5_inputs(self):
        e,_=r.helpers()
        for smoke in (True,False):
            a,b=[e.input_for(5,mode,smoke) for mode in (0,1)]
            self.assertEqual(e.no_mode(a),e.no_mode(b))
            self.assertIn('TopGridDimensions = 256 128 128',a)
            self.assertIn('dtRestartDump = -99999',a)
        self.assertGreater(2*e.budget(5),69*r.GIB)


if __name__=='__main__':unittest.main()
