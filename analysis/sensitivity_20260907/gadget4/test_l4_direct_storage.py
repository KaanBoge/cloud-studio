"""New direct-storage wrapper tests; no native solver or old experiment is run."""
import copy
import unittest
from pathlib import Path
from unittest.mock import patch

import run_l4_direct_storage as run
from gadget_controls import metadata, parameters
from gadget_l4_controls import input_values


class DirectStorageTests(unittest.TestCase):
    def mapping(self):
        return dict(target='/mnt/c', source='C:\\', fstype='9p',
                    options='rw,noatime,aname=drvfs;path=C:\\;uid=1000;gid=1000')

    def test_measured_mapping(self):
        run.mapping_gate(self.mapping(), {'drive': 'C:'}, 20, 10)

    def test_other_drive_fails(self):
        with self.assertRaises(ValueError):
            run.mapping_gate(self.mapping(), {'drive': 'D:'}, 20, 10)

    def test_non_drvfs_fails(self):
        mapping = self.mapping()
        mapping['options'] = 'rw,noatime'
        with self.assertRaises(ValueError):
            run.mapping_gate(mapping, {'drive': 'C:'}, 20, 10)

    def test_readonly_fails(self):
        mapping = self.mapping()
        mapping['options'] = mapping['options'].replace('rw,', 'ro,')
        with self.assertRaises(ValueError):
            run.mapping_gate(mapping, {'drive': 'C:'}, 20, 10)

    def test_same_device_fails(self):
        with self.assertRaises(ValueError):
            run.mapping_gate(self.mapping(), {'drive': 'C:'}, 10, 10)

    def test_full_pair_and_ancillary_are_reserved(self):
        guest = run.RESERVE + run.GUEST_ALLOWANCE
        host = guest + run.PAIR_BYTES
        run.budget_gate(guest, host, host, run.PAIR_BYTES)
        with self.assertRaises(ValueError):
            run.budget_gate(guest, host, host-1, run.PAIR_BYTES)

    def test_guest_space_never_counts_as_host_capacity(self):
        with self.assertRaises(ValueError):
            run.budget_gate(100*run.GIB, 11*run.GIB, 11*run.GIB, run.PAIR_BYTES)

    def test_host_space_never_counts_as_guest_capacity(self):
        with self.assertRaises(ValueError):
            run.budget_gate(10*run.GIB, 100*run.GIB, 100*run.GIB, run.PAIR_BYTES)

    def test_mount_free_is_independently_checked(self):
        with self.assertRaises(ValueError):
            run.budget_gate(20*run.GIB, 11*run.GIB, 100*run.GIB, run.PAIR_BYTES)

    def test_missing_host_measurement_fails(self):
        with self.assertRaises(ValueError):
            run.budget_gate(20*run.GIB, 100*run.GIB, None, run.PAIR_BYTES)

    def test_wrong_raw_destination_fails(self):
        with patch.object(run, 'RAW', Path('/home/kaan/unreviewed')):
            with self.assertRaises(ValueError):
                run.verify_paths()

    def test_remaining_budget_never_negative(self):
        with self.assertRaises(ValueError):
            run.budget_gate(20*run.GIB, 100*run.GIB, 100*run.GIB, -1)

    def test_only_path_and_metadata_times_change(self):
        text = (run.BASE/'params_L4.txt').read_text()
        old = parameters(text)
        p = metadata()
        full = input_values(text, p)
        self.assertEqual(set(old), set(full))
        changed = {k for k in old if old[k] != full[k]}
        self.assertLessEqual(changed, {'InitCondFile', 'OutputDir', 'TimeMax', 'TimeBetSnapshot', 'TimeBetStatistics'})
        self.assertEqual(float(full['TimeMax']), 5*p['t_cc'])
        self.assertEqual(float(full['TimeBetSnapshot']), p['t_cc']/20)
        self.assertEqual(full['CpuTimeBetRestartFile'], old['CpuTimeBetRestartFile'])

    def test_changed_native_numerics_fail(self):
        text = (run.BASE/'params_L4.txt').read_text().replace('CourantFac               0.15', 'CourantFac               0.3')
        self.assertNotEqual(text, (run.BASE/'params_L4.txt').read_text())
        with self.assertRaises(ValueError):
            input_values(text, metadata())

    def test_changed_pin_fails_before_run(self):
        with patch.object(run, 'sha', return_value='wrong'):
            with self.assertRaisesRegex(ValueError, 'Pinned dependency'):
                run.check_pins({'pins': {'existing-input': 'expected'}})


if __name__ == '__main__':
    unittest.main(verbosity=2)
