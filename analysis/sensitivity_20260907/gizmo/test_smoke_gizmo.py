import math,unittest
from smoke_gizmo import params,physics,ROOT

class SetupTests(unittest.TestCase):
    def test_duplicate_and_malformed_rejected(self):
        for text in ('TimeMax 1\nTimeMax 2','TimeMax 1 extra','TimeMax'):
            with self.assertRaises(ValueError):params(text)
    def test_comments(self):
        self.assertEqual(params('% comment\nTimeMax .1 # note\nBoxSize 10'),{'TimeMax':'.1','BoxSize':'10'})
    def test_recorded_mach_and_cadence(self):
        p=physics();self.assertAlmostEqual(p['v_wind'],2*math.sqrt(5/3));self.assertAlmostEqual(p['t_cc'],10/p['v_wind'])
        self.assertEqual(p['t_end_over_tcc']/p['output_dt_over_tcc'],100)
    def test_native_pair_templates_match_between_variants(self):
        for level in (3,4,5):
            a,b=[params((ROOT/f'params_{v}_L{level}.txt').read_text()) for v in ('mfm','mfv')]
            self.assertEqual(a,b);self.assertEqual(float(a['CpuTimeBetRestartFile']),3600)
            self.assertEqual(float(a['PartAllocFactor']),2.5)
            self.assertEqual(float(a['Softening_Type0']),20/(8*2**level))

if __name__=='__main__':unittest.main()
