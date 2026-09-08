"""Synthetic tests only; these do not run a solver or create scientific outputs."""
import unittest
import numpy as np
from diagnose_mfv_restart import parse_dwarf, layouts, number, take, read_prefix, energy_classes
from review_mfv_restart import output_energy

DWARF = '''
 <0><0>: Abbrev Number: 1 (DW_TAG_compile_unit)
 <1><10>: Abbrev Number: 1 (DW_TAG_base_type)
    <11> DW_AT_byte_size : 8
    <12> DW_AT_encoding : 4 (float)
 <1><20>: Abbrev Number: 1 (DW_TAG_typedef)
    <21> DW_AT_type : <0x10>
 <1><30>: Abbrev Number: 1 (DW_TAG_array_type)
    <31> DW_AT_type : <0x20>
 <2><35>: Abbrev Number: 1 (DW_TAG_subrange_type)
    <36> DW_AT_upper_bound : 2
 <2><39>: Abbrev Number: 0
 <1><40>: Abbrev Number: 1 (DW_TAG_structure_type)
    <41> DW_AT_name : (indirect string, offset: 0xaa): test
    <42> DW_AT_byte_size : 32
 <2><45>: Abbrev Number: 1 (DW_TAG_member)
    <46> DW_AT_name : Pos
    <47> DW_AT_type : <0x30>
    <48> DW_AT_data_member_location : 8
 <2><49>: Abbrev Number: 0
'''


class Tests(unittest.TestCase):
    def test_exact_padded_array_and_hierarchy(self):
        dt, ev = layouts(parse_dwarf(DWARF), {'test': ['Pos']})
        self.assertEqual(dt['test'].itemsize, 32)
        self.assertEqual(dt['test'].fields['Pos'], (np.dtype(('<f8', 3)), 8))
        self.assertEqual(ev['test']['matching_definitions'], 1)
        tabbed, _ = layouts(parse_dwarf(DWARF.replace('4 (float)', '4\t(float)')), {'test': ['Pos']})
        self.assertEqual(tabbed['test'], dt['test'])

    def test_reject_member_bounds_and_expression(self):
        for value in ('16', '2 byte block: 23 8 (DW_OP_plus_uconst: 8)'):
            with self.assertRaises(ValueError):
                layouts(parse_dwarf(DWARF.replace('location : 8', 'location : ' + value)), {'test': ['Pos']})

    def test_reject_missing_and_conflicting_definition(self):
        with self.assertRaises(ValueError):
            layouts(parse_dwarf(DWARF), {'test': ['Missing']})
        extra = '''
 <1><50>: Abbrev Number: 1 (DW_TAG_structure_type)
    <51> DW_AT_name : test
    <52> DW_AT_byte_size : 40
 <2><55>: Abbrev Number: 1 (DW_TAG_member)
    <56> DW_AT_name : Pos
    <57> DW_AT_type : <0x30>
    <58> DW_AT_data_member_location : 8
'''
        with self.assertRaises(ValueError):
            layouts(parse_dwarf(DWARF + extra), {'test': ['Pos']})

    def test_read_bounds(self):
        for position, count in ((-1, 1), (0, -1), (0, 65537), (5, 1)):
            with self.assertRaises(ValueError):
                take(b'12345678', position, '<i4', count)
        self.assertEqual(take(b'12345678', 4, '<i4', 1)[1], 8)

    def test_restart_prefix_not_whole_file(self):
        types = {x: np.dtype([('value', '<f8')]) for x in
                 ('global_data_all_processes', 'particle_data', 'gas_cell_data')}
        blob = b'\0' * 8 + (1).to_bytes(4, 'little') + b'\0' * 8 + (1).to_bytes(4, 'little') + b'\0' * 8
        with self.assertRaises(ValueError):
            read_prefix(blob, types)
        self.assertEqual(read_prefix(blob + b'TAIL', types)[-1], 32)
        for bad in (blob[:20] + (2).to_bytes(4, 'little') + blob[24:], blob[:25]):
            with self.assertRaises(ValueError):
                read_prefix(bad, types)

    def test_underflow_not_true_zero(self):
        x = np.array([0., 1e-60, 1e-45, 1.])
        c = energy_classes(x, x.astype(np.float32))
        self.assertEqual(c['native_nonpositive'], 1)
        self.assertEqual(c['exported_zero'], 2)
        self.assertEqual(c['positive_underflows'], 1)
        self.assertTrue(c['serialization_exact'])
        self.assertFalse(c['flush_to_zero_serialization_exact'])
        flushed = x.astype(np.float32); flushed[2] = 0
        fc = energy_classes(x, flushed)
        self.assertFalse(fc['serialization_exact'])
        self.assertTrue(fc['flush_to_zero_serialization_exact'])
        self.assertEqual(fc['flushed_subnormals'], 1)
        changed = x.astype(np.float32); changed[-1] = 2
        self.assertFalse(energy_classes(x, changed)['serialization_exact'])
        with self.assertRaises(ValueError):
            energy_classes([np.nan], np.array([0], dtype='f4'))

    def test_constant_integer_parser(self):
        self.assertEqual(number('0x20'), 32)
        for value in ('-1', 'DW_OP_constu: 8', '8 bytes'):
            with self.assertRaises(ValueError):
                number(value)

    def test_independent_scalar_ftz(self):
        for x in (0., 1e-141, 1e-43, 1e-38):
            self.assertEqual(output_energy(x), 0.)
        self.assertEqual(output_energy(float(np.finfo(np.float32).tiny)), float(np.finfo(np.float32).tiny))
        self.assertEqual(output_energy(1.), 1.)


if __name__ == '__main__':
    unittest.main()
