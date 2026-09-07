from pathlib import Path
import tempfile
import unittest
from tracking_validation import read_history


class HistoryValidationTests(unittest.TestCase):
    def write(self,root,name,body):
        p=Path(root)/name;p.write_text(body);return p

    def test_high_precision_frame_history(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.write(d,'a.hst','# Athena++ history\n# [1]=time [2]=frame_v [3]=frame_x\n0 0.3 0\n0.1234567891234567 0.4 0.03703703673703701\n')
            h=read_history(p);self.assertEqual(h['time'][1],.1234567891234567)

    def test_restart_header_from_parent(self):
        with tempfile.TemporaryDirectory() as d:
            parent=Path(d)/'parent';parent.mkdir();child=Path(d)/'child';child.mkdir()
            source=self.write(parent,'athinput','')
            self.write(parent,'native.hst','# Athena++\n# [1]=time [2]=frame_v [3]=frame_x\n0 0 0\n')
            p=self.write(child,'native.hst','1 0.2 0.1\n2 0.3 0.3\n')
            h=read_history(p,source);self.assertEqual(h['frame_x'][-1],.3)

    def test_missing_header_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.write(d,'native.hst','1 0.2 0.1\n')
            with self.assertRaises(ValueError):read_history(p)

    def test_nonfinite_or_wrong_column_count_refused(self):
        for rows in ('0 nan\n1 1\n','0 1 2\n1 2 3\n'):
            with tempfile.TemporaryDirectory() as d:
                p=self.write(d,'native.hst','# [1]=time [2]=frame_v\n'+rows)
                with self.assertRaises(ValueError):read_history(p)

    def test_duplicate_restart_time_uses_last_record(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.write(d,'native.hst','# [1]=time [2]=frame_v\n0 0\n1 0.1\n1 0.2\n2 0.3\n')
            h=read_history(p);self.assertEqual(list(h['time']),[0,1,2]);self.assertEqual(h['frame_v'][1],.2)

    def test_reversed_history_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.write(d,'native.hst','# [1]=time [2]=frame_v\n0 0\n2 0.2\n1 0.1\n')
            with self.assertRaises(ValueError):read_history(p)


if __name__=='__main__':unittest.main()
