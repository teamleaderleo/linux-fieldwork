#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

static void show(uint64_t v)
{
    unsigned int narrowed = (unsigned int)v;

    printf("wire=%" PRIu64 " current_uint=%u candidate_u64=%" PRIu64 "\n",
           v, narrowed, v);
}

int main(void)
{
    show(0);
    show(UINT32_MAX);
    show((uint64_t)UINT32_MAX + 1);
    show(((uint64_t)1 << 40) + 7);
    show(UINT64_MAX);
    return 0;
}
