#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

static void show(const char *name, uint64_t v)
{
    printf("%s wire=%" PRIu64 " current_uint=%u candidate_u64=%" PRIu64 "\n",
           name, v, (unsigned int)v, v);
}

int main(void)
{
    const uint64_t boundary = (uint64_t)UINT32_MAX + 1;

    show("occ", boundary);
    show("size_min", boundary + 7);
    show("size_gran", ((uint64_t)1 << 40));
    return 0;
}
