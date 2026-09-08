#include <assert.h>
#include "force_trace_core.h"

static void emit(CFTLog *log,int kind,int component,int role,uint64_t life,
                 double before,double operand,double after,int operation) {
    CFTRecord r=cft_empty(kind),saved;
    r.target=13729; r.partner=20518; r.component=component;
    r.role=role; r.lifetime=life; r.active=1; r.operation=operation;
    r.before=cft_bits(before); r.operand=cft_bits(operand); r.after=cft_bits(after);
    if(kind==CFT_LOCAL){r.arity=1;r.arg0=r.operand;}
    saved=r;
    assert(cft_append(log,&r));
    assert(memcmp(&saved,&r,sizeof(r))==0);
}
int main(int argc,char **argv) {
    CFTLog log,other;
    int c;
    if(argc!=3) return 2;
    assert(cft_format_supported());
    assert(cft_open(&log,argv[1],65536,0));
    assert(!cft_open(&other,argv[1],65536,0)); /* Existing file is untouched. */
    assert(cft_begin(&log,0.0));
    for(c=0;c<6;c++) {
        emit(&log,CFT_BASELINE,c,CFT_OWNER,0,10.,0.,10.,CFT_NONE);
        emit(&log,CFT_BASELINE,c,CFT_CACHE,1,10.,0.,10.,CFT_NONE);
        if(c>=3)emit(&log,CFT_RESET,c,CFT_OWNER,0,10.,0.,0.,CFT_ASSIGN);
        emit(&log,CFT_RESET,c,CFT_CACHE,1,10.,0.,0.,CFT_ASSIGN);
        emit(&log,CFT_LOCAL,c,CFT_CACHE,1,0.,2.,2.,CFT_ADD);
        emit(&log,CFT_REMOTE,c,CFT_OWNER,0,c>=3?0.:10.,2.,c>=3?2.:12.,CFT_ADD);
        emit(&log,CFT_LOCAL,c,CFT_OWNER,0,c>=3?2.:12.,1.,c>=3?1.:11.,CFT_SUB);
        emit(&log,CFT_FINAL,c,CFT_OWNER,0,c>=3?1.:11.,0.,c>=3?1.:11.,CFT_NONE);
    }
    assert(cft_end(&log));
    assert(cft_close(&log));
    /* A small fixed cap is a failed incomplete trace, never silent thinning. */
    assert(cft_open(&log,argv[2],8+2*sizeof(CFTRecord),1));
    assert(cft_begin(&log,0.));
    emit(&log,CFT_BASELINE,0,CFT_OWNER,0,0.,0.,0.,CFT_NONE);
    assert(!cft_end(&log));
    assert(!cft_close(&log));
    puts("C trace transport tests passed; incomplete overflow retained separately");
    return 0;
}
