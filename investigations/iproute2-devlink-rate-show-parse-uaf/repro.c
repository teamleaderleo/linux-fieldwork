/*
 * Reduced ownership/state model for iproute2 devlink rate-show.
 *
 * Build with:
 *   cc -Wall -Wextra -Werror -O1 -g -fsanitize=address \
 *      -fno-omit-frame-pointer repro.c -o /tmp/devlink-rate-show-uaf
 *   ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 /tmp/devlink-rate-show-uaf
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define HANDLEP (1ULL << 1)

struct opts {
    uint64_t present;
    char *bus_name;
    char *dev_name;
    unsigned int port_index;
};

struct dl {
    char *handle_argv;
    struct opts opts;
};

static int parse_valid(struct dl *dl, const char *arg)
{
    char *s = strdup(arg);
    char *bus_end;
    char *dev_end;

    if (!s)
        abort();

    free(dl->handle_argv);
    dl->handle_argv = s;

    bus_end = strchr(s, '/');
    if (!bus_end)
        return -1;
    *bus_end++ = '\0';

    dev_end = strchr(bus_end, '/');
    if (!dev_end)
        return -1;
    *dev_end++ = '\0';

    dl->opts.bus_name = s;
    dl->opts.dev_name = bus_end;
    dl->opts.port_index = (unsigned int)strtoul(dev_end, NULL, 10);
    dl->opts.present = HANDLEP;
    return 0;
}

/*
 * Mirrors the relevant early-error transition in current dl_argv_parse():
 * a new handle string is duplicated, the old handle_argv allocation is freed,
 * and then parsing can fail before opts.present or pointer fields are reset.
 */
static int parse_invalid(struct dl *dl, const char *arg)
{
    char *s = strdup(arg);

    if (!s)
        abort();

    free(dl->handle_argv);
    dl->handle_argv = s;

    if (!strchr(s, '/'))
        return -1;
    return 0;
}

/* Reduced stand-in for dl_opts_put() dereferencing stale string pointers. */
static void opts_put(const struct dl *dl)
{
    if (dl->opts.present & HANDLEP)
        printf("bus=%s dev=%s port=%u\n",
               dl->opts.bus_name, dl->opts.dev_name, dl->opts.port_index);
}

int main(void)
{
    struct dl dl = {0};

    if (parse_valid(&dl, "pci/0000:03:00.0/1"))
        return 1;

    if (parse_invalid(&dl, "invalid") == 0)
        return 2;

    /* Current cmd_port_fn_rate_show() ignores the parse error and proceeds. */
    opts_put(&dl);

    free(dl.handle_argv);
    return 0;
}
