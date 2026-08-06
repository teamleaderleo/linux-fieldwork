#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/uio.h>

#include "dl-utils.h"

struct systemd_subset {
    int (*sd_journal_sendv)(const struct iovec *, int);
    int (*sd_device_open)(void *, int);
};

static const struct ul_dlsym common_table[] = {
    UL_DLSYM(systemd_subset, sd_journal_sendv),
    UL_DLSYM(systemd_subset, sd_device_open),
};

static const struct ul_dlsym journal_table[] = {
    UL_DLSYM(systemd_subset, sd_journal_sendv),
};

int main(void) {
    struct systemd_subset ops = {0};
    void *handle = NULL;
    int result;

    result = ul_dlopen_symbols(
        "libsystemd.so.0",
        RTLD_NOW | RTLD_LOCAL,
        common_table,
        sizeof(common_table) / sizeof(common_table[0]),
        &ops,
        &handle);
    printf("common_result=%d handle=%p journal_pointer_after_failure=%p device_pointer=%p errno=%d\n",
           result,
           handle,
           (void *)ops.sd_journal_sendv,
           (void *)ops.sd_device_open,
           errno);
    if (result == 0 || handle != NULL) {
        fprintf(stderr, "common table unexpectedly loaded\n");
        return 10;
    }

    memset(&ops, 0, sizeof(ops));
    handle = NULL;
    errno = 0;
    result = ul_dlopen_symbols(
        "libsystemd.so.0",
        RTLD_NOW | RTLD_LOCAL,
        journal_table,
        sizeof(journal_table) / sizeof(journal_table[0]),
        &ops,
        &handle);
    printf("journal_result=%d handle=%p journal_pointer=%p errno=%d\n",
           result,
           handle,
           (void *)ops.sd_journal_sendv,
           errno);
    if (result != 0 || handle == NULL || ops.sd_journal_sendv == NULL) {
        fprintf(stderr, "journal-only table failed to load\n");
        return 20;
    }

    struct iovec iov = {
        .iov_base = (void *)"MESSAGE=probe",
        .iov_len = strlen("MESSAGE=probe"),
    };
    int call_result = ops.sd_journal_sendv(&iov, 1);
    printf("journal_call_result=%d\n", call_result);
    if (call_result != 73) {
        fprintf(stderr, "unexpected fake journal return value\n");
        return 30;
    }

    dlclose(handle);
    return 0;
}
