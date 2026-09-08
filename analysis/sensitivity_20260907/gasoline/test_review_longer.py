import copy
import unittest
import review_longer as r


class Tests(unittest.TestCase):
    def report(self):
        pairs = [('a','b'),('a','c'),('a','d'),('b','c'),('b','d'),('c','d')]
        rows = []
        for a,b in pairs:
            for step in range(6,121,6):
                rows.append(dict(first=a,second=b,snapshot=str(step),passed=True,
                    dense_membership_exact=True,required_exact_fields={'mass':True},
                    finite_precision={k:dict(passed=True,max_spacing_ratio=0,max_absolute=0)
                                      for k in ('rho','temp','vel','pos')}))
        return dict(status='test',comparisons=rows,finite_precision_comparisons_passed=True,
                    bitwise_comparisons_passed=False,
                    states=[dict(independent=dict(relative_discrepancies=[0,0,0])) for _ in range(81)])

    def test_failure_not_overridden_by_equal_mass(self):
        q=self.report();q['comparisons'][0]['passed']=False
        q['comparisons'][0]['finite_precision']['rho']['passed']=False
        q['finite_precision_comparisons_passed']=False
        x=r.summarize(q)
        self.assertFalse(x['original_test_passed'])
        self.assertTrue(x['all_dense_memberships_exact'])
        self.assertEqual(x['failed_comparisons'],1)
        self.assertEqual(x['full_science_controls_completed'],0)

    def test_incomplete_rejected(self):
        q=self.report();q['comparisons'].pop()
        with self.assertRaises(ValueError):r.summarize(q)

    def test_contradictory_status_rejected(self):
        q=self.report();q['comparisons'][0]['passed']=False
        with self.assertRaises(ValueError):r.summarize(q)

    def test_budget_includes_every_checkpoint_and_both_controls(self):
        b=r.full_budget([6000000,7000000],7869465,3145760,909387)
        self.assertEqual(b['expected_checkpoint_generations'],10)
        self.assertGreaterEqual(b['budgeted_checkpoint_generations'],10)
        self.assertEqual(b['pair_bytes'],2*b['per_case_bytes'])
        self.assertGreater(b['state_budget_bytes'],7000000+909387)
        self.assertEqual(b['independent_reserve_bytes'],10*r.GIB)

    def test_busy_workers_is_rate_not_cumulative_cpu(self):
        self.assertEqual(r.busy_workers([[0,1,0],[1,1,2],[2,1,4]]),2)


if __name__=='__main__':unittest.main()
