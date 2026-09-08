/* Isolated Gasoline adapter; caller must include its native PKD/SMF definitions. */
#ifndef CLOUD_FORCE_TRACE_NATIVE_H
#define CLOUD_FORCE_TRACE_NATIVE_H
extern int cft_native_enabled;
int cft_native_selected(const void *);
void cft_native_begin(PKD,SMF *);
void cft_native_end(PKD);
void cft_native_cache(void *);
void cft_native_pre(void *,const void *,int,int,int,double,double,double,double,int);
void cft_native_post(void *,int);
#define CFT_N_PRE(p,q,kind,c,op,term,a,b,d,n) do { \
    if(cft_native_enabled && cft_native_selected(p)) \
        cft_native_pre(p,q,kind,c,op,term,a,b,d,n); } while(0)
#define CFT_N_POST(p,c) do { \
    if(cft_native_enabled && cft_native_selected(p)) cft_native_post(p,c); } while(0)

#ifdef CLOUD_FORCE_TRACE_NATIVE_IMPLEMENTATION
#include "force_trace_core.h"
int cft_native_enabled=0;
static CFTLog cft_native_log;
static PKD cft_native_pkd;
static int cft_native_configured=0,cft_native_pending=0,cft_native_slots=0;
static uint64_t cft_native_generation=0;
static CFTRecord cft_native_event;
static void *cft_native_pending_pointer;
static struct { uintptr_t pointer; int id; uint64_t generation; } cft_native_slot[8192];

static void cft_native_fail(const char *why) {
    fprintf(stderr,"CLOUD_FORCE_TRACE_FAILED %s\n",why);
    if(cft_native_log.file)cft_close(&cft_native_log);
    abort();
}
int cft_native_selected(const void *pointer) {
    int id=((const PARTICLE *)pointer)->iOrder;
    return id==13729 || id==20518 || id==23013 || id==36578 ||
           id==54857 || id==63924 || id==64579;
}
static int cft_native_owner(const void *pointer) {
    uintptr_t p=(uintptr_t)pointer,start=(uintptr_t)cft_native_pkd->pStore;
    uintptr_t bytes=(size_t)cft_native_pkd->nLocal*sizeof(PARTICLE);
    return p>=start && p-start<bytes && (p-start)%sizeof(PARTICLE)==0;
}
static uint64_t cft_native_lifetime(const PARTICLE *p) {
    int j;
    if(cft_native_owner(p))return 0;
    for(j=0;j<cft_native_slots;j++)
        if(cft_native_slot[j].pointer==(uintptr_t)p && cft_native_slot[j].id==p->iOrder)
            return cft_native_slot[j].generation;
    cft_native_fail("unregistered cached accumulator");return 0;
}
static double cft_native_value(const PARTICLE *p,int c) {
    if(c>=0 && c<3)return p->a[c];
    if(c==3)return p->uDotPdV;
    if(c==4)return p->uDotAV;
    if(c==5)return p->uDotDiff;
    cft_native_fail("unknown force field");return 0.;
}
static void cft_native_state(PARTICLE *p,int kind) {
    CFTRecord r=cft_empty(kind);
    int c;
    r.target=p->iOrder;r.active=TYPEQueryACTIVE(p)?1:0;
    r.role=cft_native_owner(p)?CFT_OWNER:CFT_CACHE;
    r.lifetime=cft_native_lifetime(p);
    for(c=0;c<6;c++) {
        r.component=c;r.before=cft_bits(cft_native_value(p,c));r.after=r.before;
        if(!cft_append(&cft_native_log,&r))cft_native_fail("state transport/cap failure");
    }
}
static void cft_native_exit(void) {
    uint64_t total=cft_native_log.total,phases=cft_native_log.phase;
    int rank=cft_native_log.rank;
    if(!cft_native_log.file)return;
    if(cft_native_pending || !cft_close(&cft_native_log)) {
        fprintf(stderr,"CLOUD_FORCE_TRACE_FAILED unfinished trace at exit\n");
        _Exit(74);
    }
    printf("CLOUD_FORCE_TRACE_COMPLETE rank=%d phases=%llu records=%llu\n",rank,
           (unsigned long long)phases,(unsigned long long)total);
}
void cft_native_begin(PKD pkd,SMF *smf) {
    int i;char path[64];const char *setting;
    if(!cft_native_configured) {
        setting=getenv("GASOLINE_CLOUD_FORCE_TRACE");
        cft_native_enabled=setting && strcmp(setting,"1")==0;
        cft_native_configured=1;
        if(cft_native_enabled) {
            snprintf(path,sizeof(path),"force.rank%02d.bin",pkd->idSelf);
            if(!cft_open(&cft_native_log,path,64U*1024U*1024U,pkd->idSelf))
                cft_native_fail("cannot open exclusive trace or unsupported float environment");
            if(atexit(cft_native_exit)!=0)cft_native_fail("cannot register finalizer");
        }
    }
    if(!cft_native_enabled)return;
    if(cft_native_pending || cft_native_log.active)cft_native_fail("overlapping pressure phases");
    cft_native_pkd=pkd;cft_native_slots=0;cft_native_generation=0;
    if(!cft_begin(&cft_native_log,smf->dTime))cft_native_fail("phase begin failure");
    for(i=0;i<pkd->nLocal;i++)
        if(cft_native_selected(&pkd->pStore[i]))cft_native_state(&pkd->pStore[i],CFT_BASELINE);
}
void cft_native_end(PKD pkd) {
    int i;
    if(!cft_native_enabled)return;
    if(cft_native_pending || pkd!=cft_native_pkd)cft_native_fail("pressure phase ownership mismatch");
    for(i=0;i<pkd->nLocal;i++)
        if(cft_native_selected(&pkd->pStore[i]))cft_native_state(&pkd->pStore[i],CFT_FINAL);
    if(!cft_end(&cft_native_log))cft_native_fail("phase end/flush failure");
}
void cft_native_cache(void *pointer) {
    PARTICLE *p=(PARTICLE *)pointer;
    int j;
    if(!cft_native_enabled || !cft_native_selected(p))return;
    if(!cft_native_log.active || cft_native_owner(p))cft_native_fail("wrong cache initialization scope");
    for(j=0;j<cft_native_slots;j++)if(cft_native_slot[j].pointer==(uintptr_t)p)break;
    if(j==cft_native_slots) {
        if(cft_native_slots==8192)cft_native_fail("cache identity capacity exceeded");
        cft_native_slots++;
    }
    cft_native_slot[j].pointer=(uintptr_t)p;cft_native_slot[j].id=p->iOrder;
    cft_native_slot[j].generation=++cft_native_generation;
    cft_native_state(p,CFT_BASELINE);
}
void cft_native_pre(void *pointer,const void *other,int kind,int c,int op,
                    double operand,double a,double b,double d,int arity) {
    PARTICLE *p=(PARTICLE *)pointer;
    CFTRecord r=cft_empty(kind);
    if(cft_native_pending || !cft_native_log.active || !TYPEQueryACTIVE(p))
        cft_native_fail("nested, inactive or out-of-phase update");
    r.target=p->iOrder;r.partner=other?((const PARTICLE *)other)->iOrder:-1;
    r.component=c;r.operation=op;r.active=1;
    r.role=cft_native_owner(p)?CFT_OWNER:CFT_CACHE;r.lifetime=cft_native_lifetime(p);
    r.before=cft_bits(cft_native_value(p,c));r.operand=cft_bits(operand);
    r.arg0=cft_bits(a);r.arg1=cft_bits(b);r.arg2=cft_bits(d);r.arity=arity;
    cft_native_event=r;cft_native_pending_pointer=pointer;cft_native_pending=1;
}
void cft_native_post(void *pointer,int c) {
    PARTICLE *p=(PARTICLE *)pointer;
    if(!cft_native_pending || pointer!=cft_native_pending_pointer ||
        cft_native_event.component!=c || cft_native_event.target!=p->iOrder)
        cft_native_fail("unmatched force update");
    cft_native_event.after=cft_bits(cft_native_value(p,c));
    if(!cft_append(&cft_native_log,&cft_native_event))cft_native_fail("arithmetic transport/cap failure");
    cft_native_pending=0;
}
#endif
#endif
