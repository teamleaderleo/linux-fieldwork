#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef SYS_pidfd_open
#define SYS_pidfd_open 434
#endif
#ifndef SYS_pidfd_send_signal
#define SYS_pidfd_send_signal 424
#endif
#ifndef SYS_process_mrelease
#define SYS_process_mrelease 448
#endif

static void delayed_exit(int sig)
{
    (void)sig;
    usleep(300000);
    _exit(0);
}

static void child_setup(int mode, int readyfd)
{
    if (mode == 1) {
        struct sigaction sa = {0};
        sa.sa_handler = delayed_exit;
        sigemptyset(&sa.sa_mask);
        sigaction(SIGTERM, &sa, NULL);
    } else if (mode == 2) {
        signal(SIGTERM, SIG_IGN);
    }

    size_t n = 64UL << 20;
    volatile char *p = mmap(NULL, n, PROT_READ | PROT_WRITE,
                            MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED)
        _exit(111);

    for (size_t i = 0; i < n; i += 4096)
        p[i] = 1;

    if (write(readyfd, "R", 1) != 1)
        _exit(112);

    for (;;)
        pause();
}

static void one(const char *name, int mode, int sig)
{
    int pipefd[2];
    char c;

    if (pipe(pipefd)) {
        perror("pipe");
        exit(2);
    }

    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        exit(2);
    }

    if (pid == 0) {
        close(pipefd[0]);
        child_setup(mode, pipefd[1]);
        _exit(0);
    }

    close(pipefd[1]);
    if (read(pipefd[0], &c, 1) != 1) {
        perror("read ready");
        exit(2);
    }
    close(pipefd[0]);

    int pidfd = syscall(SYS_pidfd_open, pid, 0);
    if (pidfd < 0) {
        perror("pidfd_open");
        kill(pid, SIGKILL);
        waitpid(pid, NULL, 0);
        exit(2);
    }

    errno = 0;
    int sr = syscall(SYS_pidfd_send_signal, pidfd, sig, NULL, 0);
    int se = errno;

    errno = 0;
    int mr = syscall(SYS_process_mrelease, pidfd, 0);
    int me = errno;

    printf("%-24s send=%d/%s mrelease=%d/%s\n",
           name,
           sr, sr ? strerror(se) : "ok",
           mr, mr ? strerror(me) : "ok");

    if (mode == 2)
        syscall(SYS_pidfd_send_signal, pidfd, SIGKILL, NULL, 0);

    waitpid(pid, NULL, 0);
    close(pidfd);
}

int main(void)
{
    for (int i = 0; i < 5; i++)
        one("default SIGTERM", 0, SIGTERM);
    for (int i = 0; i < 5; i++)
        one("handler-delayed SIGTERM", 1, SIGTERM);
    for (int i = 0; i < 5; i++)
        one("ignored SIGTERM", 2, SIGTERM);
    for (int i = 0; i < 5; i++)
        one("SIGKILL", 0, SIGKILL);
    return 0;
}
