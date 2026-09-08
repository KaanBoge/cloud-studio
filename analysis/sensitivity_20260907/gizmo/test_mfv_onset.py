import unittest
import numpy as np
from mfv_onset import cadence,schedule,mass_account,inputs,EXPECTED_INPUT,OLD,sha


class OnsetTests(unittest.TestCase):
    def setUp(self):self.p={'TimeBegin':'0','TimeMax':'1','TimeBetSnapshot':'.1','TimeOfFirstSnapshot':'0','ComovingIntegrationOn':'0'}
    def test_native_schedule(self):
        times,_=schedule(self.p);self.assertEqual(times[0],0);self.assertEqual(times[-1],1)
        self.assertEqual(cadence(times,self.p)['actual_count'],len(times))
    def test_missing_output(self):
        times,_=schedule(self.p)
        with self.assertRaises(ValueError):cadence(times[:3]+times[4:],self.p)
    def test_replayed_time(self):
        times,_=schedule(self.p);times[4]=0
        with self.assertRaises(ValueError):cadence(times,self.p)
    def test_extra_terminal_retained(self):
        times,_=schedule(self.p);self.assertEqual(cadence(times+[1],self.p)['actual_count'],len(times)+1)
    def test_wrong_endpoint(self):
        times,_=schedule(self.p);times[-1]=1.01
        with self.assertRaises(ValueError):cadence(times,self.p)
    def test_both_mass_buffers(self):
        r=mass_account([1,2],[1.125,1.75],[0,.125],3249)
        self.assertTrue(r['passes']);self.assertTrue(r['response_detected']);self.assertEqual(r['residual'],0)
    def test_mass_loss_rejected(self):self.assertFalse(mass_account([1,2],[1,1.9],[0,0],3249)['passes'])
    def test_step_envelope(self):
        for k in [-1,32769,3.2]:
            with self.assertRaises(ValueError):mass_account([1],[1],[0],k)
    def test_invalid_mass(self):
        for args in [([1],[0],[0],1),([1],[np.nan],[0],1),([],[],[],1),([1],[1,2],[0],1)]:
            with self.assertRaises(ValueError):mass_account(*args)
    def test_unchanged_mass_is_not_response(self):self.assertFalse(mass_account([1],[1],[0],3249)['response_detected'])
    def test_original_input_and_physics(self):
        p,physics,tcc=inputs();self.assertEqual(sha(OLD/'params.txt'),EXPECTED_INPUT)
        self.assertEqual(physics['chi'],100);self.assertEqual(float(p['TimeMax']),5*tcc)
        self.assertEqual(float(p['TimeBetSnapshot']),.05*tcc)


if __name__=='__main__':unittest.main()
