import unittest
import numpy as np
import run_pairs as p


class Tests(unittest.TestCase):
    def test_only_velocity_parameter_changes(self):
        for code in p.OLD:
            for level in p.LEVELS:
                self.assertEqual(p.without_mode(p.case_input(code,level,'sharp13')),
                                 p.without_mode(p.case_input(code,level,p.OLD[code])))

    def test_rejects_wrong_historical_law(self):
        with self.assertRaises(ValueError):p.case_input('apk',3,'historical_tanh13')

    def test_native_existing_sharp_ic(self):
        for code,dirname in [('athpp','athenapp'),('apk','athenapk')]:
            folder=p.Path('/home/kaan/codes')/dirname/'runs/RESTART_sharp13_20260907_L3_chi100'
            params=p.r.parse_file(folder/'athinput')
            data=p.native(p.outputs(folder,code)[0][1],code)
            self.assertTrue(p.initial_check(data,params,code,3,'sharp13')['passed'])
            with self.assertRaises(ValueError):p.initial_check(data,params,code,3,p.OLD[code])

    def test_bad_pressure_rejected(self):
        folder=p.Path('/home/kaan/codes/athenapp/runs/RESTART_sharp13_20260907_L3_chi100')
        data=p.native(p.outputs(folder,'athpp')[0][1],'athpp');data['p']=data['p']*1.1
        with self.assertRaises(ValueError):p.initial_check(data,p.r.parse_file(folder/'athinput'),'athpp',3,'sharp13')


if __name__=='__main__':unittest.main()
