"""Strict observation-ledger checks; not a Gasoline trajectory acceptance test."""
from collections import Counter, namedtuple
import math
from pathlib import Path
import struct
import sys

MAGIC=b'CFTv1\0\0\0'
RECORD=struct.Struct('<4Q8i8Q')
ROW=namedtuple('Row','sequence phase time_bits lifetime rank target partner kind '
    'component operation active role before operand after arg0 arg1 arg2 arity reserved')
TARGETS=(13729,20518,23013,36578,54857,63924,64579)
BEGIN,BASELINE,RESET,LOCAL,REMOTE,FINAL,END=range(1,8)
NONE,ADD,SUB,ASSIGN=range(4)
OWNER,CACHE=range(2)
CAP=64*1024**2


def bits(value):
    return struct.unpack('<Q',struct.pack('<d',value))[0]


def number(value):
    result=struct.unpack('<d',struct.pack('<Q',value))[0]
    if not math.isfinite(result):raise ValueError('Nonfinite trace value')
    return result


def apply(before,operation,operand):
    x,y=number(before),number(operand)
    if operation==ADD:result=x+y
    elif operation==SUB:result=x-y
    elif operation==ASSIGN:result=y
    else:raise ValueError('Unknown arithmetic operation')
    if not math.isfinite(result):raise ValueError('Nonfinite replay result')
    return bits(result)


def term(row):
    if not 1<=row.arity<=3:raise ValueError('Local operand needs explicit factor arity')
    factors=(row.arg0,row.arg1,row.arg2)
    if any(factors[row.arity:]):raise ValueError('Nonzero unused factor slots')
    x=number(factors[0])
    for factor in factors[1:row.arity]:x=x*number(factor)
    if not math.isfinite(x) or bits(x)!=row.operand:
        raise ValueError('Recorded operand fails independent factor replay')


def rows(data):
    if not isinstance(data,bytes) or len(data)>CAP or not data.startswith(MAGIC):
        raise ValueError('Unsupported or oversized trace')
    if (len(data)-len(MAGIC))%RECORD.size:raise ValueError('Truncated record')
    for offset in range(len(MAGIC),len(data),RECORD.size):
        yield ROW(*RECORD.unpack_from(data,offset))


def validate(data):
    if sys.float_info.mant_dig!=53 or sys.float_info.radix!=2 or sys.float_info.rounds!=1:
        raise ValueError('Unsupported independent replay float environment')
    current=None;last_phase=0;rank=None;last_time=-math.inf;count=0
    states={};finals=set();summary=[];kinds=Counter()
    for row in rows(data):
        count+=1;kinds[row.kind]+=1
        if row.sequence!=count or row.rank<0 or row.reserved:
            raise ValueError('Bad sequence, rank or reserved field')
        if rank is None:rank=row.rank
        if rank!=row.rank:raise ValueError('Mixed ranks in one stream')
        now=number(row.time_bits)
        if row.kind==BEGIN:
            if current is not None or row.phase!=last_phase+1 or now<last_time:
                raise ValueError('Nested, skipped or backward phase')
            current=(row.phase,row.time_bits);states={};finals=set()
        elif current!=(row.phase,row.time_bits):
            raise ValueError('Event outside its native phase')
        if row.kind in (BEGIN,END):
            if (row.target,row.partner,row.component)!=(-1,-1,-1) or any((row.lifetime,
                row.operation,row.active,row.role,row.before,row.operand,row.after,
                row.arg0,row.arg1,row.arg2,row.arity)):
                raise ValueError('Malformed phase marker')
            if row.kind==END:
                owners={key for key in states if key[1]==OWNER}
                if owners!=finals:raise ValueError('Missing owner final state')
                groups={(key[0],key[1],key[2]) for key in states}
                for target,role,life in groups:
                    if {key[3] for key in states if key[:3]==(target,role,life)}!=set(range(6)):
                        raise ValueError('Incomplete six-field accumulator')
                summary.append(dict(phase=row.phase,time_code=now,
                    owner_ids=sorted({key[0] for key in owners}),
                    cache_lifetimes=sum(g[1]==CACHE for g in groups)))
                current=None;last_phase=row.phase;last_time=now
            continue
        if row.target not in TARGETS or row.partner < -1 or not 0<=row.component<6:
            raise ValueError('Unexpected target or component')
        if row.role not in (OWNER,CACHE) or (row.role==OWNER)!=(row.lifetime==0):
            raise ValueError('Owner/cache lifetime mismatch')
        key=(row.target,row.role,row.lifetime,row.component)
        for value in (row.before,row.operand,row.after):number(value)
        if row.kind in (BASELINE,FINAL):
            if row.operation!=NONE or row.operand or row.arity or any((row.arg0,row.arg1,row.arg2)):
                raise ValueError('Malformed observation-only state')
            if row.before!=row.after:raise ValueError('Observation changed its own value')
            if row.kind==BASELINE:
                if key in states:raise ValueError('Reused accumulator lifetime')
                states[key]=row.after
            else:
                if row.role!=OWNER or key in finals or states.get(key)!=row.before:
                    raise ValueError('Wrong, duplicate or discontinuous owner final')
                finals.add(key)
            continue
        if row.kind not in (RESET,LOCAL,REMOTE) or not row.active or key in finals:
            raise ValueError('Unexpected or inactive accumulation')
        if states.get(key)!=row.before:raise ValueError('Missing event or wrong accumulator baseline')
        if row.kind==RESET:
            if row.operation!=ASSIGN or row.arity or any((row.arg0,row.arg1,row.arg2)):
                raise ValueError('Malformed initialization event')
            if row.operand!=bits(0.) or (row.role==OWNER and row.component<3):
                raise ValueError('Not the reviewed native initializer')
        else:
            if row.operation not in (ADD,SUB):raise ValueError('Not an addition/subtraction')
            if row.kind==LOCAL:term(row)
            elif row.role!=OWNER or row.operation!=ADD or row.arity or any((row.arg0,row.arg1,row.arg2)):
                raise ValueError('Remote subtotal is not an owner combine')
        if apply(row.before,row.operation,row.operand)!=row.after:
            raise ValueError('Native arithmetic differs from exact-bit replay')
        states[key]=row.after
    if current is not None or not summary:raise ValueError('Incomplete or empty trace')
    return dict(status='passed_trace_structure_and_selected_arithmetic',rank=rank,
        records=count,phases=summary,event_counts=dict(kinds),
        trajectory_gate_cleared=False,
        limits=['Selected recorded fields only; native insertion coverage requires separate review.',
                'Recorded cache lifetimes need not include a separate outgoing-packet capture.',
                'Trace validity is not proof of no instrumentation effect or trajectory equivalence.'])


def validate_case(streams):
    if len(streams)!=2:raise ValueError('Original two-worker case requires two streams')
    reports=sorted((validate(data) for data in streams),key=lambda x:x['rank'])
    if [r['rank'] for r in reports]!=[0,1]:raise ValueError('Missing or duplicate native rank')
    a,b=reports[0]['phases'],reports[1]['phases']
    if len(a)!=len(b):raise ValueError('Rank phase counts differ')
    for pa,pb in zip(a,b):
        if pa['phase']!=pb['phase'] or bits(pa['time_code'])!=bits(pb['time_code']):
            raise ValueError('Native phase/time mismatch across workers')
        owners=pa['owner_ids']+pb['owner_ids']
        if sorted(owners)!=list(TARGETS):raise ValueError('Missing or duplicate selected owner')
    return dict(status='passed_two_rank_selected_trace_coverage',ranks=reports,
                trajectory_gate_cleared=False)


def replay_terms(initial,terms):
    value=initial
    for operation,operand in terms:value=apply(value,operation,operand)
    return value


def compare_orders(initial_a,terms_a,final_a,initial_b,terms_b,final_b):
    if replay_terms(initial_a,terms_a)!=final_a or replay_terms(initial_b,terms_b)!=final_b:
        raise ValueError('Reported endpoints do not match observed-order replay')
    if initial_a!=initial_b:return 'different_starting_values'
    if Counter(terms_a)!=Counter(terms_b):return 'different_contribution_population_or_values'
    if final_a==final_b:return 'no_endpoint_difference'
    return 'observed_order_explains_this_selected_accumulator'


if __name__=='__main__':
    import json
    if len(sys.argv)!=2:raise SystemExit('Use: force_trace_replay.py TRACE.bin')
    path=Path(sys.argv[1])
    if path.stat().st_size>CAP:raise ValueError('Trace exceeds fixed per-rank budget')
    print(json.dumps(validate(path.read_bytes()),indent=2,allow_nan=False))
