import unittest
from trace_mfv_mass_update import mass_summary,limiter_probe

class Tests(unittest.TestCase):
    def test_fixed_conserved_mass_with_nonzero_flux(self):
        s=mass_summary([1,2],[1.1,2],[1,2],[0,0],[.1,-.1])
        self.assertEqual(s['conserved_mass_different_from_ic'],0)
        self.assertEqual(s['predicted_mass_different_from_conserved'],1)
        self.assertEqual(s['nonzero_DtMass'],2)
        self.assertEqual(s['nonzero_accumulated_dMass'],0)

    def test_real_mass_change_not_hidden(self):
        self.assertEqual(mass_summary([1,2],[1,2.1],[1,2.1],[0,.1],[0,.2])['conserved_mass_different_from_ic'],1)

    def test_bad_arrays_rejected(self):
        for args in (([],[],[],[],[]),([1],[1,2],[1],[0],[0]),([0],[0],[0],[0],[0]),([1],[float('nan')],[1],[0],[0])):
            with self.assertRaises(ValueError):mass_summary(*args)

    def test_endpoint_probe_not_executed_step(self):
        p=limiter_probe(1e-100,-.01,1e-17)
        self.assertTrue(p['would_half_limit'])
        self.assertLess(p['trial_after_one_clock_quantum'],0)
        self.assertAlmostEqual(p['max_dt_before_half_limit']/5e-99,1)
        self.assertFalse(limiter_probe(1,.01,.1)['would_half_limit'])
        with self.assertRaises(ValueError):limiter_probe(0,-1,1)

if __name__=='__main__':unittest.main()
