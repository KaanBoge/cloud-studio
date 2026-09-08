import math,unittest
import numpy as np
from run_full_l3 import input_for,check_times,budget,physics,params,ROOT,WALL_LIMIT,STOP_GRACE

class FullL3Tests(unittest.TestCase):
    def test_only_output_times_change(self):
        for variant in ('mfm','mfv'):
            old=params((ROOT/f'params_{variant}_L3.txt').read_text());new=params(input_for(variant))
            self.assertEqual(set(old),set(new))
            self.assertEqual({k:old[k] for k in old if k not in ('TimeMax','TimeBetSnapshot')},{k:new[k] for k in new if k not in ('TimeMax','TimeBetSnapshot')})
            p=physics();self.assertEqual(float(new['TimeMax']),5*p['t_cc']);self.assertEqual(float(new['TimeBetSnapshot']),.05*p['t_cc'])
    def test_unvalidated_level_and_variant_rejected(self):
        for variant,level in (('mfm',4),('mfv',5),('unknown',3)):
            with self.assertRaises(ValueError):input_for(variant,level)
    def test_full_cadence_and_extra_actual_terminal(self):
        p=physics();times=np.linspace(0,5,101)*p['t_cc']
        self.assertEqual(check_times(times,p)['native_snapshots'],101)
        result=check_times(np.append(times,times[-1]),p)
        self.assertEqual(result['native_snapshots'],102);self.assertEqual(result['distinct_header_times'],101)
    def test_missing_or_replayed_times_rejected(self):
        p=physics();times=np.linspace(0,5,101)*p['t_cc']
        for bad in (np.delete(times,30),np.concatenate([times[:40],times[20:]]),np.append(times[:-2],[times[-2],times[-2]])):
            with self.assertRaises(ValueError):check_times(bad,p)
    def test_budget_retains_every_snapshot_and_two_restarts(self):
        for variant in ('mfm','mfv'):
            b=budget(variant)
            self.assertGreater(b['case_bytes'],104*b['snapshot_bytes']+2*b['measured_restart_set_bytes'])
            self.assertEqual(b['pair_bytes'],2*b['case_bytes'])
    def test_no_third_restart_generation_before_forced_exit(self):
        self.assertLess(WALL_LIMIT+STOP_GRACE+30,2*3600)

if __name__=='__main__':unittest.main()
