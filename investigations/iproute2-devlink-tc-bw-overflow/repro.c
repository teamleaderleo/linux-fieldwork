/* Reduced reproduction of iproute2 devlink tc-bw conversion behavior. */
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static int checked_integer(int *val, const char *arg)
{
    char *end;
    long res;

    errno = 0;
    res = strtol(arg, &end, 10);
    if (end == arg || *end)
        return -1;
    if ((res == LONG_MIN || res == LONG_MAX) && errno == ERANGE)
        return -1;
    if (res < INT_MIN || res > INT_MAX)
        return -1;
    *val = (int)res;
    return 0;
}

static int checked_u32(uint32_t *val, const char *arg)
{
    char *end;
    unsigned long res;

    errno = 0;
    res = strtoul(arg, &end, 10);
    if (end == arg || *end)
        return -1;
    if (res == ULONG_MAX && errno == ERANGE)
        return -1;
    if (res > UINT32_MAX)
        return -1;
    *val = (uint32_t)res;
    return 0;
}

static void probe(const char *index, const char *bandwidth)
{
    char *end;
    int current_index;
    uint32_t current_bw;
    int candidate_index = 0;
    uint32_t candidate_bw = 0;
    int index_err;
    int bw_err;

    current_index = (int)strtoul(index, &end, 10);
    current_bw = (uint32_t)strtoul(bandwidth, &end, 10);

    index_err = checked_integer(&candidate_index, index);
    bw_err = checked_u32(&candidate_bw, bandwidth);

    printf("idx=%s bw=%s | current idx=%d bw=%u | candidate idx=",
           index, bandwidth, current_index, current_bw);
    if (index_err)
        printf("ERR");
    else
        printf("%d", candidate_index);
    printf(" bw=");
    if (bw_err)
        printf("ERR");
    else
        printf("%u", candidate_bw);
    putchar('\n');
}

int main(void)
{
    probe("0", "20");
    probe("4294967296", "20");
    probe("4294967297", "20");
    probe("0", "4294967296");
    probe("0", "4294967297");
    probe("-4294967296", "20");
    return 0;
}
