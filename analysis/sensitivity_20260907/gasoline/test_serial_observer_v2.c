/* Synthetic tests of observation logic; no solver invocation. */
#include "serial_observer_v2.h"
int main(void) {
    unsigned char data[16],original[16];
    int counts[5] = {4,4,4,4,5};
    CLOUD_SERIAL_COPY copy;
    assert(cloudSerialInitialPath("state.initial"));
    assert(cloudSerialInitialPath("./state.initial"));
    assert(!cloudSerialInitialPath("state.initial.extra"));
    assert(!cloudSerialInitialPath("state.000006"));
    assert(!cloudSerialInitialPath(NULL));
    memset(data,0x59,sizeof(data));
    memcpy(original,data,sizeof(data));
    copy=cloudSerialCapture(data,4,counts);
    assert(cloudSerialEqual(&copy,data,4,counts));
    data[7]^=1;
    assert(!cloudSerialEqual(&copy,data,4,counts));
    data[7]^=1;
    counts[2]++;
    assert(!cloudSerialEqual(&copy,data,4,counts));
    counts[2]--;
    assert(!cloudSerialEqual(&copy,data,3,counts));
    assert(!memcmp(data,original,sizeof(data)));
    cloudSerialReport(&copy,data,4,counts,"synthetic");
    cloudSerialRelease(&copy);
    assert(copy.bytes==NULL);
    puts("PASS: unchanged, changed byte, changed metadata, length, preservation, release");
    return 0;
}
