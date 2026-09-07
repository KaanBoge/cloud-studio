import copy
import unittest
from unittest.mock import patch
import queue_more as m


class QueueTests(unittest.TestCase):
    def setUp(self):
        # Definition tests model unused L3 destinations even after the real
        # campaign has completed. No real directory is removed or changed.
        exists=m.Path.exists
        self.target_patch=patch.object(m.Path,'exists',lambda path:
            False if path.name.startswith('RESTART_sharp13_20260907_L3_chi') else exists(path))
        self.target_patch.start()
        self.addCleanup(self.target_patch.stop)

    def test_all_18_definitions_verified_without_writing(self):
        jobs=[m.definition(c,l,x) for l in (3,5,6) for x in (10,100,1000) for c in ('athpp','apk')]
        self.assertEqual(len({j['directory'] for j in jobs}),18)
        for j in jobs:
            m.verify_unchanged(j)
            self.assertEqual(j['target_native_times'],101)
        self.assertGreater(jobs[-1]['required_with_safety_gib'],245)

    def test_modified_binary_or_input_cannot_run(self):
        job=m.definition('athpp',3,10)
        for field in ('binary_sha256','parameter_sha256'):
            bad=copy.deepcopy(job); bad[field]='altered'
            with self.assertRaisesRegex(RuntimeError,'changed'):
                m.verify_unchanged(bad)

    def test_unsupported_level_rejected(self):
        with self.assertRaises(ValueError):m.q.profile_for('athpp',2)

    def test_original_l4_profile_stays_same(self):
        p=m.q.profile_for('athpp')
        self.assertEqual((p['level'],p['block'],p['ranks']),(4,32,16))
        self.assertNotIn('hdf5_compression_level',m.q.profile_for('apk',4))

    def test_real_existing_destination_is_never_overwritten(self):
        with patch.object(m.Path,'exists',return_value=True):
            with self.assertRaisesRegex(RuntimeError,'already exists'):
                m.definition('athpp',3,10)


if __name__=='__main__': unittest.main()
