import unittest
import numpy as np
from mfv_short_controls import mass_account,parameters,validate_inputs,OLD


class ShortTests(unittest.TestCase):
    def test_conservative_response(self):
        r=mass_account([1,2],[1.25,1.75],[.125,-.125],4)
        self.assertTrue(r['passes']);self.assertTrue(r['response_detected'])
        self.assertEqual(r['residual'],0)

    def test_pending_flux_is_separate(self):
        r=mass_account([1,2],[1,1.875],[0,.125],4)
        self.assertTrue(r['passes']);self.assertEqual(r['conserved'],2.875)
        self.assertEqual(r['pending'],.125);self.assertEqual(r['combined'],3)

    def test_lost_pending_mass_fails(self):
        self.assertFalse(mass_account([1,2],[1,1.875],[0,0],4)['passes'])

    def test_no_mass_response_is_not_a_repair(self):
        r=mass_account([1,2],[1,2],[0,0],4)
        self.assertTrue(r['passes']);self.assertFalse(r['response_detected'])

    def test_invalid_mass_arrays(self):
        for args in [([1],[1,2],[0],1),([1],[0],[0],1),([1],[np.nan],[0],1),([],[],[],1)]:
            with self.assertRaises(ValueError):mass_account(*args)

    def test_step_envelope(self):
        for steps in [-1,257,1.5]:
            with self.assertRaises(ValueError):mass_account([1],[1],[0],steps)

    def test_duplicate_parameters(self):
        with self.assertRaises(ValueError):parameters('TimeMax .1\nTimeMax .2\n')

    def test_numerics_cannot_change(self):
        text=(OLD/'params.txt').read_text()
        self.assertEqual(float(validate_inputs(text)['TimeMax']),.1)
        with self.assertRaises(ValueError):validate_inputs(text.replace('0.05','0.04'))


if __name__=='__main__':unittest.main()
