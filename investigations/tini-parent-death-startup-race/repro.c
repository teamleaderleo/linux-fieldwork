#define _GNU_SOURCE
#include <sys/prctl.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static int signal_pending(int sig) {
    sigset_t pending;
    if (sigpending(&pending) != 0) _exit(8);
    return sigismember(&pending, sig) == 1;
}

static int run_case(int with_ppid_check) {
    int ready[2], report[2];
    if (pipe(ready) || pipe(report)) { perror("pipe"); exit(2); }

    pid_t middle = fork();
    if (middle < 0) { perror("fork middle"); exit(2); }
    if (middle == 0) {
        close(report[0]);
        pid_t subject = fork();
        if (subject < 0) _exit(3);
        if (subject == 0) {
            sigset_t mask;
            sigemptyset(&mask);
            sigaddset(&mask, SIGUSR1);
            if (sigprocmask(SIG_BLOCK, &mask, NULL) != 0) _exit(4);

            pid_t original_parent = getppid();
            char b = 'R';
            if (write(ready[1], &b, 1) != 1) _exit(5);

            // Model time spent in argument/signal setup before Tini installs PDEATHSIG.
            usleep(50000);
            if (prctl(PR_SET_PDEATHSIG, SIGUSR1) != 0) _exit(6);

            if (with_ppid_check && getppid() != original_parent) {
                if (kill(getpid(), SIGUSR1) != 0) _exit(7);
            }

            char out = signal_pending(SIGUSR1) ? '1' : '0';
            if (write(report[1], &out, 1) != 1) _exit(9);
            _exit(0);
        }

        char b;
        close(ready[1]);
        if (read(ready[0], &b, 1) != 1) _exit(10);
        // Direct parent exits after subject has captured its identity, but before prctl().
        _exit(0);
    }

    close(ready[0]); close(ready[1]); close(report[1]);
    waitpid(middle, NULL, 0);

    char out = '?';
    ssize_t n = read(report[0], &out, 1);
    close(report[0]);
    if (n != 1) {
        fprintf(stderr, "no report for case %d\n", with_ppid_check);
        return 2;
    }

    printf("%s: SIGUSR1-pending=%c\n",
           with_ppid_check ? "ppid-check-order" : "current-order", out);
    return out == '1' ? 0 : 1;
}

int main(void) {
    int current = run_case(0);
    int checked = run_case(1);
    return (current == 1 && checked == 0) ? 0 : 1;
}
