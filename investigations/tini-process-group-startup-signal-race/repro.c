#define _GNU_SOURCE
#include <sys/types.h>
#include <sys/wait.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void run_model(const char *name, int iters, int parent_sets_group) {
    int forwarded = 0, esrch = 0, other = 0, child_usr1 = 0;

    for (int i = 0; i < iters; i++) {
        sigset_t mask, oldmask;
        sigemptyset(&mask);
        sigaddset(&mask, SIGUSR1);
        if (sigprocmask(SIG_BLOCK, &mask, &oldmask) != 0) { perror("sigprocmask block"); exit(2); }

        // Model a signal that reaches Tini after signal blocking but before spawn.
        if (raise(SIGUSR1) != 0) { perror("raise"); exit(2); }

        pid_t pid = fork();
        if (pid < 0) { perror("fork"); exit(2); }
        if (pid == 0) {
            if (setpgid(0, 0) != 0) _exit(111);
            if (sigprocmask(SIG_SETMASK, &oldmask, NULL) != 0) _exit(112);
            pause();
            _exit(0);
        }

        if (parent_sets_group) {
            if (setpgid(pid, pid) != 0 && errno != EACCES && errno != ESRCH) {
                perror("parent setpgid"); exit(2);
            }
        }

        siginfo_t si;
        if (sigwaitinfo(&mask, &si) != SIGUSR1) { perror("sigwaitinfo"); exit(2); }

        if (kill(-pid, SIGUSR1) == 0) {
            forwarded++;
        } else if (errno == ESRCH) {
            esrch++;
            kill(pid, SIGKILL);
        } else {
            other++;
            kill(pid, SIGKILL);
        }

        int status = 0;
        if (waitpid(pid, &status, 0) != pid) { perror("waitpid"); exit(2); }
        if (WIFSIGNALED(status) && WTERMSIG(status) == SIGUSR1) child_usr1++;

        if (sigprocmask(SIG_SETMASK, &oldmask, NULL) != 0) { perror("sigprocmask restore"); exit(2); }
    }

    printf("%s: iters=%d forwarded=%d ESRCH=%d other=%d child-died-SIGUSR1=%d\n",
           name, iters, forwarded, esrch, other, child_usr1);
}

int main(int argc, char **argv) {
    int iters = argc > 1 ? atoi(argv[1]) : 5000;
    run_model("current-order", iters, 0);
    run_model("parent-setpgid-order", iters, 1);
    return 0;
}
