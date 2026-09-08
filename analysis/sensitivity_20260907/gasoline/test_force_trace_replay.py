import unittest
import force_trace_replay as f


def row(kind,component=-1,**kw):
    values=dict(zip(f.ROW._fields,[0]*len(f.ROW._fields)))
    values.update(phase=1,time_bits=f.bits(0.),rank=0,target=-1,partner=-1,
                  kind=kind,component=component)
    if component>=0:values.update(target=f.TARGETS[0],active=1)
    values.update(kw)
    return f.ROW(**values)


def encode(records):
    return f.MAGIC+b''.join(f.RECORD.pack(*r._replace(sequence=i+1)) for i,r in enumerate(records))


def valid_records():
    result=[row(f.BEGIN)]
    for c in range(6):
        result.append(row(f.BASELINE,c,before=f.bits(10.),after=f.bits(10.)))
        result.append(row(f.LOCAL,c,operation=f.ADD,before=f.bits(10.),operand=f.bits(6.),
            after=f.bits(16.),arg0=f.bits(2.),arg1=f.bits(3.),arity=2))
        result.append(row(f.FINAL,c,before=f.bits(16.),after=f.bits(16.)))
    result.append(row(f.END))
    return result


class TraceTests(unittest.TestCase):
    def test_schema_and_valid(self):
        self.assertEqual(f.RECORD.size,128)
        got=f.validate(encode(valid_records()))
        self.assertEqual(got['records'],20)
        self.assertFalse(got['trajectory_gate_cleared'])

    def test_failed_replay_not_tolerance_adjustment(self):
        r=valid_records();r[2]=r[2]._replace(after=f.bits(17.))
        with self.assertRaisesRegex(ValueError,'exact-bit'):f.validate(encode(r))

    def test_missing_event(self):
        r=valid_records();del r[2]
        with self.assertRaises(ValueError):f.validate(encode(r))

    def test_factor_mismatch(self):
        r=valid_records();r[2]=r[2]._replace(arg0=f.bits(4.))
        with self.assertRaisesRegex(ValueError,'factor replay'):f.validate(encode(r))

    def test_signed_zero(self):
        self.assertNotEqual(f.bits(-0.),f.bits(0.))
        self.assertEqual(f.apply(f.bits(-0.),f.ADD,f.bits(-0.)),f.bits(-0.))
        self.assertEqual(f.apply(f.bits(-0.),f.ADD,f.bits(0.)),f.bits(0.))

    def test_reordered_same_terms(self):
        a=[(f.ADD,f.bits(2.**53)),(f.ADD,f.bits(1.)),(f.SUB,f.bits(2.**53))]
        b=[a[0],a[2],a[1]]
        self.assertEqual(f.compare_orders(f.bits(0.),a,f.bits(0.),f.bits(0.),b,f.bits(1.)),
            'observed_order_explains_this_selected_accumulator')

    def test_changed_contributions_are_not_order_proof(self):
        self.assertEqual(f.compare_orders(f.bits(0.),[(f.ADD,f.bits(1.))],f.bits(1.),
            f.bits(0.),[(f.ADD,f.bits(2.))],f.bits(2.)),
            'different_contribution_population_or_values')

    def test_incomplete_and_truncated(self):
        for raw in (b'',f.MAGIC,encode(valid_records())[:-1],encode(valid_records()[:-1])):
            with self.assertRaises(ValueError):f.validate(raw)

    def test_nonfinite(self):
        r=valid_records();r[1]=r[1]._replace(before=f.bits(float('nan')))
        with self.assertRaises(ValueError):f.validate(encode(r))

    def test_inactive_missing_or_unknown_target(self):
        for field,value in [('active',0),('target',12),('role',7),('reserved',1)]:
            r=valid_records();r[2]=r[2]._replace(**{field:value})
            with self.assertRaises(ValueError):f.validate(encode(r))

    def test_cache_lifetimes_and_reset(self):
        r=valid_records();cached=[]
        for life in (1,2):
            for c in range(6):
                cached.append(row(f.BASELINE,c,role=f.CACHE,lifetime=life,
                    before=f.bits(10.),after=f.bits(10.)))
                cached.append(row(f.RESET,c,role=f.CACHE,lifetime=life,operation=f.ASSIGN,
                    before=f.bits(10.),operand=f.bits(0.),after=f.bits(0.)))
        r=r[:-1]+cached+r[-1:]
        self.assertEqual(f.validate(encode(r))['phases'][0]['cache_lifetimes'],2)
        duplicate=r[:-1]+[cached[0]]+r[-1:]
        with self.assertRaisesRegex(ValueError,'Reused'):f.validate(encode(duplicate))

    def test_wrong_sequence_rank_or_phase(self):
        raw=encode(valid_records())
        second=f.ROW(*f.RECORD.unpack_from(raw,8+128))
        for field,value in [('sequence',9),('rank',1),('phase',2)]:
            changed=raw[:136]+f.RECORD.pack(*second._replace(**{field:value}))+raw[264:]
            with self.assertRaises(ValueError):f.validate(changed)

    def test_terminal_state_required_for_all_six_fields(self):
        r=valid_records();del r[-2]
        with self.assertRaisesRegex(ValueError,'final state'):f.validate(encode(r))

    def test_two_workers_complete_owner_union(self):
        a=[row(f.BEGIN)]
        for target in f.TARGETS:
            a.extend(r._replace(target=target) for r in valid_records()[1:-1])
        a.append(row(f.END))
        b=[row(f.BEGIN,rank=1),row(f.END,rank=1)]
        result=f.validate_case([encode(a),encode(b)])
        self.assertFalse(result['trajectory_gate_cleared'])
        with self.assertRaises(ValueError):f.validate_case([encode(a),encode(a)])
        with self.assertRaisesRegex(ValueError,'selected owner'):
            f.validate_case([encode(valid_records()),encode(b)])

    def test_owner_acceleration_is_not_zero_initialized(self):
        r=valid_records()
        r[2]=row(f.RESET,0,before=f.bits(10.),operation=f.ASSIGN,after=f.bits(0.))
        with self.assertRaisesRegex(ValueError,'native initializer'):f.validate(encode(r))


if __name__=='__main__':unittest.main()
