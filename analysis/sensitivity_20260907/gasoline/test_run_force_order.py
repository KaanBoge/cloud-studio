import json
import unittest
import run_force_order as runner


class RunnerTests(unittest.TestCase):
    def test_exact_declared_cases_and_environment(self):
        origin=runner.ROOT/'longer_validation_2rank_v1/retained_on'
        base=json.loads((origin/'native_environment.json').read_text())
        for name in runner.NAMES:
            env=runner.environment(base,name)
            self.assertEqual(env['GASOLINE_CLOUD_INITIAL_OUTPUT'],'1' if name=='on' else '0')
            self.assertEqual(env['GASOLINE_CLOUD_KEEP_CHECKPOINTS'],'1')
            self.assertEqual(env['GASOLINE_CLOUD_FORCE_TRACE'],'1')
            self.assertEqual(env['PKDGRAV_CHECKPOINT_FDL'],base['PKDGRAV_CHECKPOINT_FDL'])
            self.assertNotIn('GASOLINE_CLOUD_SERIAL_AUDIT',env)
        with self.assertRaises(ValueError):runner.environment(base,'retry')

    def test_only_duration_changes(self):
        old=(runner.ROOT/'longer_validation_2rank_v1/retained_on/run.param').read_text()
        before=runner.common.parameters(old);after=runner.common.parameters(runner.common.input_six(old))
        self.assertEqual({k for k in before if before[k]!=after[k]},{'nSteps'})
        self.assertEqual(after['nSteps'],'6')
        self.assertEqual(after['iOutInterval'],'6')
        self.assertEqual(after['iCheckInterval'],'60')

    def test_wrong_checkpoint_environment_rejected(self):
        with self.assertRaises(ValueError):runner.environment({},'off_a')

    def test_native_build_pin(self):
        self.assertEqual(runner.sha(runner.TREE/'gasoline/gasoline'),runner.BINARY_SHA)


if __name__=='__main__':unittest.main()
