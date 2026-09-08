import unittest
import compare_force_order as c

f = c.f


def row(kind, component=0, **kwargs):
    d = dict.fromkeys(f.ROW._fields, 0)
    d.update(kind=kind, component=component, target=f.TARGETS[0], partner=-1,
             phase=1, active=1)
    d.update(kwargs)
    return f.ROW(**d)


def records(values=(1., 2.), *, initial=0., component=0, reset=False, rank=0):
    current = f.bits(initial)
    result = [row(f.BASELINE, component, before=current, after=current, rank=rank)]
    if reset:
        result.append(row(f.RESET, component, operation=f.ASSIGN,
                          before=current, after=f.bits(0.), rank=rank))
        current = f.bits(0.)
    for value in values:
        operand = f.bits(value)
        after = f.apply(current, f.ADD, operand)
        result.append(row(f.LOCAL, component, operation=f.ADD, partner=42,
                          before=current, operand=operand, after=after,
                          arg0=operand, arity=1, rank=rank))
        current = after
    result.append(row(f.FINAL, component, before=current, after=current, rank=rank))
    return [r._replace(sequence=i + 1) for i, r in enumerate(result)]


def group(*args, **kwargs):
    return next(iter(c.group_owners([records(*args, **kwargs)]).values()))


class CompareTests(unittest.TestCase):
    def test_owner_not_cache(self):
        rr = records()
        cache = [r._replace(role=f.CACHE, lifetime=2) for r in rr]
        self.assertEqual(len(c.group_owners([rr + cache])), 1)

    def test_rank_not_identity(self):
        aa = c.group_owners([records(rank=0)])
        bb = c.group_owners([records(rank=1)])
        got = c.compare_pair('a', aa, 'b', bb)
        self.assertEqual(got['endpoint_differences'], 0)

    def test_duplicate_owner_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            c.group_owners([records(rank=0), records(rank=1)])

    def test_reset_retains_old_baseline(self):
        a = group(initial=99., component=3, reset=True)
        b = group(initial=1., component=3, reset=True)
        self.assertNotEqual(a['baseline'], b['baseline'])
        self.assertEqual(c.classify(a, b), 'no_endpoint_difference')

    def test_late_reset_rejected(self):
        rr = records(component=3, reset=True)
        rr[1], rr[2] = rr[2], rr[1]
        with self.assertRaisesRegex(ValueError, 'late'):
            c.group_owners([rr])

    def test_repeated_reset_rejected(self):
        rr = records(component=3, reset=True)
        rr.insert(2, rr[1])
        with self.assertRaisesRegex(ValueError, 'repeated'):
            c.group_owners([rr])

    def test_reordered_identical_strict_tokens(self):
        a = group((2.**53, 1., -2.**53))
        b = group((2.**53, -2.**53, 1.))
        self.assertEqual(c.classify(a, b), c.ORDER)

    def test_changed_provenance_not_order_proof(self):
        a = group((2.**53, 1., -2.**53))
        b = group((2.**53, -2.**53, 1.))
        b['events'][0] = b['events'][0]._replace(partner=43)
        self.assertEqual(c.classify(a, b), 'different_contribution_population_or_values')

    def test_changed_initial(self):
        self.assertEqual(c.classify(group(initial=1.), group(initial=2.)), 'different_starting_values')

    def test_changed_population_equal_endpoint_still_classified(self):
        self.assertEqual(c.classify(group((1., 2.)), group((3.,))),
                         'different_contribution_population_or_values')

    def test_false_endpoint_rejected(self):
        a, b = group(), group()
        a['final'] = f.bits(7.)
        with self.assertRaises(ValueError):
            c.classify(a, b)

    def test_missing_final_and_mismatched_time(self):
        with self.assertRaisesRegex(ValueError, 'final'):
            c.group_owners([records()[:-1]])
        aa = c.group_owners([records()])
        bb = c.group_owners([[r._replace(time_bits=f.bits(1.)) for r in records()]])
        with self.assertRaisesRegex(ValueError, 'populations'):
            c.compare_pair('a', aa, 'b', bb)

    def test_hex_preserves_signed_zero(self):
        self.assertEqual(c.hx(f.bits(-0.)), '0x8000000000000000')
        self.assertNotEqual(c.hx(f.bits(-0.)), c.hx(f.bits(0.)))


if __name__ == '__main__':
    unittest.main()
