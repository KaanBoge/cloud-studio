/* Read-only diagnostic of live particle bytes across native serial output.
 * No floating-point calculations or writes to native particle storage.
 */
#ifndef CLOUD_SERIAL_OBSERVER_H
#define CLOUD_SERIAL_OBSERVER_H
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

typedef struct {
    unsigned char *bytes;
    size_t length;
    int counts[5];
} CLOUD_SERIAL_COPY;

static int cloudSerialInitialPath(const char *path) {
    return path != NULL && (strcmp(path,"state.initial") == 0
                           || strcmp(path,"./state.initial") == 0);
}

static CLOUD_SERIAL_COPY cloudSerialCapture(const void *data, size_t itemsize,
                                           const int counts[5]) {
    CLOUD_SERIAL_COPY result;
    assert(counts[0] > 0 && counts[0] <= 65536 && itemsize > 0 && itemsize <= 1024);
    result.length = (size_t)counts[0]*itemsize;
    result.bytes = (unsigned char *)malloc(result.length);
    assert(result.bytes != NULL);
    memcpy(result.bytes,data,result.length);
    memcpy(result.counts,counts,sizeof(result.counts));
    return result;
}

static int cloudSerialEqual(const CLOUD_SERIAL_COPY *before, const void *data,
                            size_t itemsize, const int counts[5]) {
    if (memcmp(before->counts,counts,sizeof(before->counts)) != 0) return 0;
    if (before->length != (size_t)counts[0]*itemsize) return 0;
    return memcmp(before->bytes,data,before->length) == 0;
}

static void cloudSerialReport(const CLOUD_SERIAL_COPY *before, const void *data,
                              size_t itemsize, const int counts[5], const char *stage) {
    int equal;
    equal = cloudSerialEqual(before,data,itemsize,counts);
    printf("CLOUD_SERIAL_OBSERVER {\"stage\":\"%s\",\"count\":%d,\"bytes\":%lu,\"equal\":%s}\n",
           stage,before->counts[0],(unsigned long)before->length,equal?"true":"false");
}

static void cloudSerialRelease(CLOUD_SERIAL_COPY *copy) {
    free(copy->bytes);
    copy->bytes = NULL;
}
#endif
