/* Observation-only binary trace transport. No native solver dependency. */
#ifndef CLOUD_FORCE_TRACE_CORE_H
#define CLOUD_FORCE_TRACE_CORE_H
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <float.h>
#include <fenv.h>
#include <fcntl.h>
#include <unistd.h>

enum { CFT_BEGIN=1, CFT_BASELINE, CFT_RESET, CFT_LOCAL, CFT_REMOTE,
       CFT_FINAL, CFT_END };
enum { CFT_NONE=0, CFT_ADD=1, CFT_SUB=2, CFT_ASSIGN=3 };
enum { CFT_OWNER=0, CFT_CACHE=1 };
typedef struct {
    uint64_t sequence, phase, time_bits, lifetime;
    int32_t rank, target, partner, kind, component, operation, active, role;
    uint64_t before, operand, after, arg0, arg1, arg2, arity, reserved;
} CFTRecord;
typedef char cft_record_size_must_be_128[(sizeof(CFTRecord)==128)?1:-1];
typedef struct {
    FILE *file;
    CFTRecord *buffer;
    size_t count, capacity;
    uint64_t total, phase, time_bits;
    int32_t rank;
    int active, failed;
} CFTLog;

static uint64_t cft_bits(double x) {
    uint64_t value; memcpy(&value,&x,8); return value;
}
static int cft_format_supported(void) {
    uint32_t endian=1;
    return sizeof(double)==8 && DBL_MANT_DIG==53 && FLT_RADIX==2 &&
        *(unsigned char *)&endian==1 && fegetround()==FE_TONEAREST;
}
static int cft_open(CFTLog *log,const char *path,size_t max_bytes,int rank) {
    int fd;
    memset(log,0,sizeof(*log));
    if (!cft_format_supported() || rank<0 || max_bytes<8+2*sizeof(CFTRecord) ||
        max_bytes>64U*1024U*1024U) return 0;
    log->capacity=(max_bytes-8)/sizeof(CFTRecord);
    log->buffer=(CFTRecord *)malloc(log->capacity*sizeof(CFTRecord));
    if (!log->buffer) return 0;
    fd=open(path,O_WRONLY|O_CREAT|O_EXCL,0600);
    if (fd<0) { free(log->buffer); log->buffer=NULL; return 0; }
    log->file=fdopen(fd,"wb");
    if (!log->file) { close(fd); free(log->buffer); log->buffer=NULL; return 0; }
    if (fwrite("CFTv1\0\0\0",1,8,log->file)!=8) {
        fclose(log->file); free(log->buffer); memset(log,0,sizeof(*log)); return 0;
    }
    log->rank=rank;
    return 1;
}
static int cft_append(CFTLog *log,const CFTRecord *input) {
    CFTRecord *out;
    if (!log->file || log->failed || !log->active ||
        log->total>=log->capacity || log->count>=log->capacity) {
        log->failed=1; return 0;
    }
    out=&log->buffer[log->count++];
    *out=*input; /* All record fields must be initialized by the caller. */
    out->sequence=++log->total;
    out->rank=log->rank; out->phase=log->phase; out->time_bits=log->time_bits;
    return 1;
}
static CFTRecord cft_empty(int kind) {
    CFTRecord r;
    memset(&r,0,sizeof(r)); r.kind=kind; r.target=-1; r.partner=-1;
    r.component=-1;
    return r;
}
static int cft_begin(CFTLog *log,double native_time) {
    CFTRecord r=cft_empty(CFT_BEGIN);
    if (!log->file || log->active || log->failed) { log->failed=1; return 0; }
    log->phase++; log->time_bits=cft_bits(native_time); log->active=1;
    return cft_append(log,&r);
}
static int cft_end(CFTLog *log) {
    CFTRecord r=cft_empty(CFT_END);
    if (!cft_append(log,&r)) return 0;
    log->active=0;
    /* Disk writes occur only after the caller closes the native pressure phase. */
    if (fwrite(log->buffer,sizeof(CFTRecord),log->count,log->file)!=log->count ||
        fflush(log->file)!=0) { log->failed=1; return 0; }
    log->count=0;
    return 1;
}
static int cft_close(CFTLog *log) {
    int ok;
    if (!log->file) return 0;
    ok=!log->active && !log->failed;
    /* Preserve buffered failure evidence too, without inventing an END marker. */
    if (log->count && fwrite(log->buffer,sizeof(CFTRecord),log->count,log->file)!=log->count) ok=0;
    if (fclose(log->file)!=0) ok=0;
    free(log->buffer); log->buffer=NULL; log->file=NULL; log->count=0;
    return ok;
}
#endif
