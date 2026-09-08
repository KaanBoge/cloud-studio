"""Read-only measurements of the failed exact-equivalence check; no acceptance."""
import json
import numpy as np
import gasoline_controls as g
from verify_instrumentation_v3 import iorder

def compare(a,b):
    _,x=g.read(a);_,y=g.read(b)
    x=x[np.argsort(iorder(a,len(x)))];y=y[np.argsort(iorder(b,len(y)))]
    result={}
    for k in g.GAS.names:
        xv=x[k].astype(float);yv=y[k].astype(float)
        result[k]=dict(unequal_values=int(np.count_nonzero(xv!=yv)),
                       max_absolute=float(np.max(abs(xv-yv))),
                       max_scaled_to_reference_peak=float(np.max(abs(xv-yv))/max(float(np.max(abs(xv))),1e-30)))
    return result

if __name__=='__main__':
    report=dict(status='diagnostic_only_exact_equivalence_failed',comparisons=[])
    for first,second in [('original_tanh','off_tanh'),('off_tanh','on_tanh'),('original_tanh','on_tanh')]:
        for file in ('state.000003','state.000006'):
            report['comparisons'].append(dict(first=first,second=second,snapshot=file,
                fields=compare(g.WORK/first/file,g.WORK/second/file)))
    report['initial_pair']=compare(g.WORK/'on_tanh/state.initial',g.WORK/'on_sharp/state.initial')
    g.write_new(g.ROOT/'instrumentation_difference_audit.json',report)
    print(json.dumps(report,indent=2))
