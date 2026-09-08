"""Replay the pinned Gadget-4 run.cc output scheduler, not an empirical tolerance."""
import math
import numpy as np

def expected_times(values):
    if int(values['OutputListOn'])!=0 or int(values['ComovingIntegrationOn'])!=0:raise ValueError('Unsupported native scheduler branch')
    begin=float(values['TimeBegin']);end=float(values['TimeMax']);time=float(values['TimeOfFirstSnapshot']);interval=float(values['TimeBetSnapshot'])
    if begin!=0 or interval<=0 or end<=begin:raise ValueError('Invalid native schedule')
    timebase=1<<29;unit=(end-begin)/timebase;limit=int(float(values['MaxSizeTimestep'])/unit)
    block=timebase
    while block>limit:block>>=1
    if block==0:raise ValueError('Timestep below native integer range')
    result=[];n=0
    while time<=end:
        integer=int((time-begin)/unit)
        rounded=int(integer/float(block)+.5)*block
        stamp=begin+rounded*unit
        if not result or stamp>result[-1]:result.append(stamp)
        time+=interval;n+=1
        if n>10000:raise ValueError('Unexpected output schedule length')
    # run.cc writes a final state if there has not already been one there.
    if result[-1]!=end:result.append(end)
    return np.array(result),unit,block*unit

def cadence(times,p,values):
    times=np.array(times,float);expected,unit,block=expected_times(values)
    if len(times)!=len(expected) or not np.all(np.isfinite(times)) or np.any(np.diff(times)<=0):raise ValueError('Native scheduled state missing/repeated; retain and review')
    error=float(np.max(abs(times-expected)))
    bound=8*np.finfo(float).eps*max(1,float(values['TimeMax']))
    if error>bound:raise ValueError(f'Native headers differ from exact pinned scheduler: {error} > {bound}')
    if abs(times[-1]-5*p['t_cc'])>bound:raise ValueError('Wrong terminal physical time')
    return dict(native_snapshots=len(times),distinct_header_times=len(np.unique(times)),scheduled_count=101,
        integer_timebase=1<<29,integer_time_unit_code=unit,native_output_block_code=block,
        exact_scheduler_max_absolute_error=error,roundoff_bound=bound,
        policy='Native run.cc rounds each requested time to nearest power-of-two MaxSizeTimestep block, possibly early or late. All native headers unchanged. Exact extra/repeated states require review, never silent filtering.')
