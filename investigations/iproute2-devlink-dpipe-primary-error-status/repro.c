#include <stdio.h>

static int current_table_show(int resource_result, int table_result)
{
    int err = resource_result;

    if (err == 0) {
        /* Optional resource enrichment succeeded. */
    }
    (void)table_result; /* Current primary receive result is discarded. */
    return 0;
}

static int candidate_table_show(int resource_result, int table_result)
{
    int err = resource_result;

    if (err == 0) {
        /* Optional resource enrichment succeeded. */
    }
    err = table_result;
    return err;
}

static int current_table_dump(int header_result, int entries_result)
{
    int err = header_result;

    if (err)
        return err;
    (void)entries_result; /* Current primary entries result is discarded. */
    return err;
}

static int candidate_table_dump(int header_result, int entries_result)
{
    int err = header_result;

    if (err)
        return err;
    err = entries_result;
    return err;
}

int main(void)
{
    printf("show optional-resource-fail primary-ok: current=%d candidate=%d\n",
           current_table_show(-95, 0), candidate_table_show(-95, 0));
    printf("show optional-resource-fail primary-fail: current=%d candidate=%d\n",
           current_table_show(-95, -22), candidate_table_show(-95, -22));
    printf("show resource-ok primary-fail: current=%d candidate=%d\n",
           current_table_show(0, -22), candidate_table_show(0, -22));
    printf("dump headers-ok entries-fail: current=%d candidate=%d\n",
           current_table_dump(0, -22), candidate_table_dump(0, -22));
    printf("dump headers-fail: current=%d candidate=%d\n",
           current_table_dump(-95, -22), candidate_table_dump(-95, -22));
    return 0;
}
