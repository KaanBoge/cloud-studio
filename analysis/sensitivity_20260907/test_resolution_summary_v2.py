"""Test only the new report merge, not old extraction or native calculations."""
import copy
import unittest
import extend_resolution_summary_v2 as x


class TestSummaryExtension(unittest.TestCase):
    def setUp(self):
        self.old=x.read(x.ROOT/'resolution_summary_v1/summary.json')
        self.docs={code:x.read(x.ROOT/info[0]) for code,info in x.ADDITIONS.items()}
    def test_counts(self):
        pairs,counts=x.extend(self.old,self.docs)
        self.assertEqual(counts,dict(accepted_pairs=25,accepted_full_controls=50,native_states_in_accepted_analysis=5054))
        self.assertEqual(pairs[:23],self.old['pairs'])
    def test_duplicate(self):
        with self.assertRaises(ValueError):x.validate_pairs(self.old['pairs']+[self.old['pairs'][0]])
    def test_scope(self):
        self.old['pairs'][0]['chi']=10
        with self.assertRaises(ValueError):x.extend(self.old,self.docs)
    def test_wrong_resolution(self):
        self.old['pairs'][0]['dimensions_streamwise']=[65,32,32]
        with self.assertRaises(ValueError):x.extend(self.old,self.docs)
    def test_missing_law(self):
        del self.old['pairs'][0]['variants']['sharp']
        with self.assertRaises(ValueError):x.extend(self.old,self.docs)
    def test_shifted_denominator(self):
        self.docs['GIZMO MFV (repaired)']['metrics']['4']['initial_dense_mass']+=1
        with self.assertRaises(ValueError):x.extend(self.old,self.docs)
    def test_changed_metric_units(self):
        self.old['pairs'][0]['peak_dense_mass_separation_percent']*=100
        with self.assertRaises(ValueError):x.extend(self.old,self.docs)
    def test_incomplete_native_times(self):
        self.docs['GIZMO MFV (repaired)']['cases_by_level']['4'][0]['rows'].pop()
        with self.assertRaises(ValueError):x.extend(self.old,self.docs)
    def test_unaccepted_new_source(self):
        self.docs['Gadget-4 SPH']['status']='failed'
        with self.assertRaises(ValueError):x.extend(self.old,self.docs)
    def test_missing_or_changed_recipe(self):
        self.docs['Gadget-4 SPH']['cases_by_level']['4'][0]['binary_sha256']='wrong'
        with self.assertRaises(ValueError):x.extend(self.old,self.docs)
    def test_native_endpoints_preserved(self):
        pairs,_=x.extend(self.old,self.docs)
        old_times=[v['last_t_over_tcc'] for p in self.old['pairs'] for v in p['variants'].values()]
        new_times=[v['last_t_over_tcc'] for p in pairs[:23] for v in p['variants'].values()]
        self.assertGreater(max(old_times),5)
        self.assertEqual(old_times,new_times)
    def test_outside_existing_summary_envelope(self):
        self.old['pairs'][0]['variants']['sharp']['last_t_over_tcc']=4.7
        with self.assertRaises(ValueError):x.extend(self.old,self.docs)


if __name__=='__main__':unittest.main()
