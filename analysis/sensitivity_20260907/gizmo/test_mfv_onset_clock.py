import unittest
from review_mfv_onset import clock_schedule,verify_clock


class ClockTests(unittest.TestCase):
    def setUp(self):self.p={'TimeBegin':'0','TimeMax':'1','TimeBetSnapshot':'.1','TimeOfFirstSnapshot':'0','ComovingIntegrationOn':'0'}
    def test_native_sixty_bit_tick(self):self.assertEqual(clock_schedule(self.p)[1],2.**-60)
    def test_source_schedule(self):
        times,_=clock_schedule(self.p);self.assertEqual(verify_clock(times,self.p)['max_schedule_offset'],0)
    def test_missing_state(self):
        times,_=clock_schedule(self.p)
        with self.assertRaises(ValueError):verify_clock(times[:3]+times[4:],self.p)
    def test_replayed_state(self):
        times,_=clock_schedule(self.p);times[4]=0
        with self.assertRaises(ValueError):verify_clock(times,self.p)
    def test_old_broad_tolerance_is_not_used(self):
        times,_=clock_schedule(self.p);times[4]+=1e-9
        with self.assertRaises(ValueError):verify_clock(times,self.p)
    def test_extra_terminal_retained(self):
        times,_=clock_schedule(self.p);self.assertEqual(verify_clock(times+[1],self.p)['actual_count'],len(times)+1)


if __name__=='__main__':unittest.main()
