#include <stdio.h>

static int current_wrapper(int recv_result)
{
    int err;

    err = recv_result;
    (void)err;
    return 0;
}

static int candidate_wrapper(int recv_result)
{
    int err;

    err = recv_result;
    return err;
}

int main(void)
{
    const int cases[] = {0, -1, -22, -95};
    unsigned int i;

    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        printf("recv=%d current=%d candidate=%d\n",
               cases[i], current_wrapper(cases[i]), candidate_wrapper(cases[i]));
    }
    return 0;
}
