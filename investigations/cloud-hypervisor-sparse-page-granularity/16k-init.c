// SPDX-License-Identifier: Apache-2.0
// Minimal initramfs PID 1 for the real 16 KiB sparse-test discriminator.

#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/reboot.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static void die(const char *what)
{
    dprintf(STDERR_FILENO, "FATAL: %s: %s\n", what, strerror(errno));
    sync();
    reboot(LINUX_REBOOT_CMD_RESTART);
    _exit(111);
}

static void require(int condition, const char *what)
{
    if (!condition) {
        dprintf(STDERR_FILENO, "FATAL: %s\n", what);
        sync();
        reboot(LINUX_REBOOT_CMD_RESTART);
        _exit(112);
    }
}

static void wait_for_block_device(const char *path)
{
    struct stat st;

    for (int i = 0; i < 100; i++) {
        if (stat(path, &st) == 0 && S_ISBLK(st.st_mode))
            return;
        usleep(100000);
    }

    errno = ENOENT;
    die("virtio block device did not appear");
}

static int run_sparse_tests(const char *binary, const char *label)
{
    pid_t pid = fork();
    if (pid < 0)
        die("fork");

    if (pid == 0) {
        char *const argv[] = {
            (char *)binary,
            (char *)"sparse::unit_tests",
            (char *)"--nocapture",
            (char *)"--test-threads=1",
            NULL,
        };

        setenv("TMPDIR", "/tmp", 1);
        setenv("RUST_BACKTRACE", "1", 1);
        execv(binary, argv);
        die("execv sparse test binary");
    }

    int status;
    if (waitpid(pid, &status, 0) < 0)
        die("waitpid");

    if (WIFEXITED(status)) {
        int rc = WEXITSTATUS(status);
        dprintf(STDOUT_FILENO, "%s_RC=%d\n", label, rc);
        return rc;
    }

    if (WIFSIGNALED(status)) {
        int sig = WTERMSIG(status);
        dprintf(STDOUT_FILENO, "%s_SIGNAL=%d\n", label, sig);
        return 128 + sig;
    }

    dprintf(STDOUT_FILENO, "%s_STATUS=UNKNOWN\n", label);
    return 255;
}

int main(void)
{
    if (mkdir("/dev", 0755) < 0 && errno != EEXIST)
        die("mkdir /dev");
    if (mount("devtmpfs", "/dev", "devtmpfs", 0, NULL) < 0)
        die("mount devtmpfs");

    if (mkdir("/proc", 0555) < 0 && errno != EEXIST)
        die("mkdir /proc");
    if (mount("proc", "/proc", "proc", 0, NULL) < 0)
        die("mount proc");

    if (mkdir("/tmp", 01777) < 0 && errno != EEXIST)
        die("mkdir /tmp");

    long page_size = sysconf(_SC_PAGESIZE);
    dprintf(STDOUT_FILENO, "PAGE_SIZE=%ld\n", page_size);
    require(page_size == 16384, "guest kernel does not use 16 KiB base pages");

    wait_for_block_device("/dev/vda");
    if (mount("/dev/vda", "/tmp", "ext4", 0, NULL) < 0)
        die("mount 4 KiB-block ext4 scratch disk");

    const int baseline_rc = run_sparse_tests("/baseline-vmm-tests", "BASELINE");
    const int candidate_rc = run_sparse_tests("/candidate-vmm-tests", "CANDIDATE");

    require(baseline_rc != 0, "baseline unexpectedly passed on the 16 KiB kernel");
    require(candidate_rc == 0, "candidate sparse tests failed on the 16 KiB kernel");

    dprintf(STDOUT_FILENO, "REAL_16K_PASS\n");
    sync();
    reboot(LINUX_REBOOT_CMD_RESTART);
    _exit(0);
}
