import copy
import json
from pathlib import Path
import tempfile
import unittest
from run_corrected_athpp import make_input
from run_params import parse_file
from comparison_checks import require_common_physics
from figure2_v2 import load_runs


class ComparisonTests(unittest.TestCase):
    def make(self,root,name,mach=2,chi=10,level=3):
        path=Path(root)/name;path.write_text(make_input(level,chi,mach))
        p=parse_file(path);nx=8*2**level
        return {'schema_version':2,'kind':'athpp','parameters':p,'comparison_group':'same-name',
                'initial_grid':{'finest_equivalent_dimensions':[nx,nx//2,nx//2],
                                'uniform':True,'domain_width_over_R':[20,10,10]},
                'series':[{'time_code':0,'t_over_tcc':0,'dense_mass_over_initial_dense_mass':1},
                          {'time_code':p['t_cc'],'t_over_tcc':1,'dense_mass_over_initial_dense_mass':.5}]}

    def test_same_physics_across_chi_and_resolution_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            require_common_physics([self.make(d,'a'),self.make(d,'b',chi=100,level=4)])

    def test_matching_group_name_cannot_hide_different_mach(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'mach'):
                require_common_physics([self.make(d,'a'),self.make(d,'b',mach=.5)])

    def test_edited_intermediate_metadata_caught(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.make(d,'a');a['parameters']['chi']=100
            with self.assertRaisesRegex(ValueError,'chi'):require_common_physics([a])

    def test_changed_native_input_caught(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.make(d,'a');Path(a['parameters']['source']).write_text(make_input(3,100))
            with self.assertRaises(ValueError):require_common_physics([a])

    def test_changed_time_scale_caught(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.make(d,'a');a['series'][1]['t_over_tcc']=5
            with self.assertRaisesRegex(ValueError,'time'):require_common_physics([a])

    def test_missing_units_not_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.make(d,'a');a['parameters']['r_cloud']=None
            with self.assertRaises(ValueError):require_common_physics([a])

    def test_wrong_code_label_caught(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.make(d,'a');a['kind']='flash'
            with self.assertRaisesRegex(ValueError,'label'):require_common_physics([a])

    def test_wrong_domain_caught(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.make(d,'a');a['initial_grid']['domain_width_over_R']=[40,10,10]
            with self.assertRaisesRegex(ValueError,'Domain'):require_common_physics([a])

    def test_figure2_negative_mass_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.make(d,'a');a['series'][1]['dense_mass_over_initial_dense_mass']=-.1
            f=Path(d)/'diagnostic.json';f.write_text(json.dumps(a))
            with self.assertRaisesRegex(ValueError,'negative'):load_runs([f])

    def test_variant_cannot_enter_fixed_frame_nonradiative_group(self):
        for extra in ('\n<cooling>\nintegrator = townsend\n', '\n<problem>\ngalilean_shift = true\n'):
            with tempfile.TemporaryDirectory() as d:
                a=self.make(d,'a');p=Path(a['parameters']['source'])
                p.write_text(p.read_text()+extra);a['parameters']=parse_file(p)
                with self.assertRaises(ValueError):require_common_physics([a])


if __name__=='__main__':unittest.main()
