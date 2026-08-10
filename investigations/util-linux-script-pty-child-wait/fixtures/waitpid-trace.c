#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static pid_t (*real_fork_fn)(void);
static pid_t (*real_waitpid_fn)(pid_t, int *, int);
static int trace_fd = STDERR_FILENO;

static void init_symbols(void)
{
        const char *value;

        if (!real_fork_fn)
                real_fork_fn = dlsym(RTLD_NEXT, "fork");
        if (!real_waitpid_fn)
                real_waitpid_fn = dlsym(RTLD_NEXT, "waitpid");

        value = getenv("LF_WAITTRACE_FD");
        if (value)
                trace_fd = atoi(value);
}

pid_t fork(void)
{
        pid_t rc;
        int saved_errno;

        init_symbols();
        rc = real_fork_fn();
        saved_errno = errno;

        if (rc > 0)
                dprintf(trace_fd, "pid=%d fork() -> child=%d\n",
                        (int) getpid(), (int) rc);

        errno = saved_errno;
        return rc;
}

pid_t waitpid(pid_t pid, int *status, int options)
{
        pid_t rc;
        int saved_errno;

        init_symbols();
        rc = real_waitpid_fn(pid, status, options);
        saved_errno = errno;

        dprintf(trace_fd,
                "pid=%d waitpid(arg=%d, options=0x%x) -> %d errno=%d\n",
                (int) getpid(), (int) pid, options, (int) rc, saved_errno);

        errno = saved_errno;
        return rc;
}
