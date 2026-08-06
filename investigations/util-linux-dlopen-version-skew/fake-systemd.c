#include <stdio.h>
#include <sys/uio.h>

int sd_journal_sendv(const struct iovec *iov, int n) {
    (void)iov;
    fprintf(stderr, "fake sd_journal_sendv invoked with %d vectors\n", n);
    return 73;
}
