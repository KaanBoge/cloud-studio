import subprocess
import unittest
from unittest.mock import patch
import storage_guard as s


class StorageTests(unittest.TestCase):
    def sample(self, guest, host):
        return {'filesystem_free_bytes':guest*s.GIB,
                'windows_backing_volume':{'drive':'C:', 'free_bytes':host*s.GIB},
                'effective_free_bytes':min(guest,host)*s.GIB}

    def test_guest_free_does_not_override_full_host(self):
        with self.assertRaisesRegex(RuntimeError, 'Windows C:'):
            s.require_storage(self.sample(168,35),38*s.GIB)

    def test_safety_reserve_is_required(self):
        with self.assertRaises(RuntimeError):
            s.require_storage(self.sample(168,35),30*s.GIB)

    def test_small_test_with_reserve_fits(self):
        s.require_storage(self.sample(168,35),2*s.GIB)

    def test_guest_can_be_the_bottleneck(self):
        with self.assertRaises(RuntimeError):
            s.require_storage(self.sample(8,500),2*s.GIB)

    def test_host_lookup_missing_fails_closed(self):
        with patch.dict(s.os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):s.windows_backing_volume()

    def test_wrong_distribution_fails_closed(self):
        with patch.object(s.shutil,'which',return_value='/fake/powershell.exe'), \
             patch.object(s.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'[{"distribution":"different"}]',b'')):
            with self.assertRaises(RuntimeError):s.windows_backing_volume('Ubuntu')

    def test_negative_budget_rejected(self):
        with self.assertRaises(ValueError):s.require_storage(self.sample(100,100),-1)


if __name__=='__main__':unittest.main()
