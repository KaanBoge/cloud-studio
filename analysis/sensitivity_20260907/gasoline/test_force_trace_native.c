/* Synthetic adapter integration, not a simulation or full native ABI test. */
#include <stdlib.h>
#include <assert.h>
typedef struct { int iOrder,active; double a[3],uDotPdV,uDotAV,uDotDiff; } PARTICLE;
typedef struct { PARTICLE *pStore; int nLocal,idSelf; } FakePKD;
typedef FakePKD *PKD;
typedef struct { double dTime; } SMF;
#define TYPEQueryACTIVE(p) ((p)->active)
#define CLOUD_FORCE_TRACE_NATIVE_IMPLEMENTATION
#include "force_trace_native.h"

static double *field(PARTICLE *p,int c) {
    if(c<3)return &p->a[c];
    if(c==3)return &p->uDotPdV;
    if(c==4)return &p->uDotAV;
    return &p->uDotDiff;
}
static void init(PARTICLE *p,int owner) {
    int c;
    if(!owner)cft_native_cache(p);
    if(TYPEQueryACTIVE(p))for(c=owner?3:0;c<6;c++) {
        CFT_N_PRE(p,NULL,CFT_RESET,c,CFT_ASSIGN,0.,0.,0.,0.,0);
        *field(p,c)=0.;
        CFT_N_POST(p,c);
    }
}
int main(int argc,char **argv) {
    PARTICLE owner[7],cached,incoming;
    FakePKD fake;
    const int ids[7]={13729,20518,23013,36578,54857,63924,64579};
    int rank,i,c,phase;SMF smf;
    if(argc!=2)return 2;
    rank=atoi(argv[1]);assert(rank==0 || rank==1);
    fake.pStore=owner;fake.nLocal=0;fake.idSelf=rank;
    for(i=0;i<7;i++)if(i%2==rank) {
        PARTICLE *p=&owner[fake.nLocal++];
        p->iOrder=ids[i];p->active=1;
        for(c=0;c<6;c++)*field(p,c)=10.;
    }
    assert(setenv("GASOLINE_CLOUD_FORCE_TRACE","1",1)==0);
    for(phase=0;phase<2;phase++) {
        smf.dTime=phase*0.03227486122;
        cft_native_begin((PKD)&fake,&smf);
        for(i=0;i<fake.nLocal;i++) {
            PARTICLE *p=&owner[i];
            init(p,1);
            for(c=0;c<6;c++) {
                double before=*field(p,c);
                CFT_N_PRE(p,NULL,CFT_LOCAL,c,CFT_ADD,2.*3.,2.,3.,0.,2);
                *field(p,c)+=2.*3.;
                CFT_N_POST(p,c);
                assert(*field(p,c)==before+6.);
            }
            incoming=*p;
            for(c=0;c<6;c++)*field(&incoming,c)=2.;
            for(c=0;c<6;c++) {
                CFT_N_PRE(p,&incoming,CFT_REMOTE,c,CFT_ADD,*field(&incoming,c),0.,0.,0.,0);
                *field(p,c)+=*field(&incoming,c);
                CFT_N_POST(p,c);
            }
        }
        cached=owner[0];cached.iOrder=ids[1-rank];
        init(&cached,0);
        for(c=0;c<6;c++) {
            CFT_N_PRE(&cached,&owner[0],CFT_LOCAL,c,CFT_SUB,1.,1.,0.,0.,1);
            *field(&cached,c)-=1.;
            CFT_N_POST(&cached,c);
        }
        init(&cached,0); /* Same address/ID, new explicit cache lifetime. */
        cached.active=0;
        init(&cached,0); /* Inactive cached fields are observed but not reset. */
        cft_native_end((PKD)&fake);
    }
    puts("Synthetic native adapter checks passed");
    return 0;
}
