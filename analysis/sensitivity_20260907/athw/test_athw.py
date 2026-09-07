import unittest
import re
import run_athw as r
class Tests(unittest.TestCase):
    def test_only_velocity_changes(self):
        for level in r.LEVELS:
            a=re.sub(r'velocity_ic_tanh = [01]','',r.input_for(level,0))
            b=re.sub(r'velocity_ic_tanh = [01]','',r.input_for(level,1))
            self.assertEqual(a,b)
    def test_invalid_mode_rejected(self):
        with self.assertRaises(ValueError):r.input_for(3,2)
    def test_smokes_verified_and_binary_matched(self):
        p=r.json.loads((r.ROOT/'smoke_batch.json').read_text())
        b=r.json.loads((r.ROOT/'build.json').read_text())
        self.assertEqual(p['status'],'complete_native_checks')
        self.assertEqual(len(p['finished']),2)
        for result in p['finished']:
            self.assertEqual(result['binary_sha256'],b['binary_sha256'])
            self.assertIn('initial_checks',result['series'][0])
if __name__=='__main__':unittest.main()
