#include <stdio.h>
#include <stdlib.h>

struct fragment_entry { unsigned long long start; unsigned int size; };

static void current_check(unsigned int fragment, unsigned int count)
{
    if (fragment > count) {
        puts("current: rejected");
        return;
    }
    printf("current: accepted index %u for table count %u\n", fragment, count);
}

static void candidate_check(unsigned int fragment, unsigned int count)
{
    if (fragment >= count) {
        puts("candidate: rejected");
        return;
    }
    printf("candidate: accepted index %u for table count %u\n", fragment, count);
}

int main(void)
{
    unsigned int count = 1;
    unsigned int fragment = 1; /* exactly one past the only valid index 0 */
    struct fragment_entry *table = calloc(count, sizeof(*table));
    if (!table) return 1;

    current_check(fragment, count);
    candidate_check(fragment, count);
    puts("valid indexes for a one-entry allocation are only [0]");

    /* Do not dereference table[fragment] in this reduced fixture; the exact
       source does so after the current check, and the allocation/count proof
       is the discriminator. */
    free(table);
    return 0;
}
