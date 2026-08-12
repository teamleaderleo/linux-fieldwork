#define _GNU_SOURCE

#include <errno.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <linux/filter.h>
#include <linux/seccomp.h>

#ifndef __NR_mount_setattr
#error "__NR_mount_setattr is required for this test helper"
#endif

static int
install_filter (void)
{
  struct sock_filter filter[] = {
    BPF_STMT (BPF_LD | BPF_W | BPF_ABS, offsetof (struct seccomp_data, nr)),
    BPF_JUMP (BPF_JMP | BPF_JEQ | BPF_K, __NR_mount_setattr, 0, 1),
    BPF_STMT (BPF_RET | BPF_K,
              SECCOMP_RET_ERRNO | (ENOSYS & SECCOMP_RET_DATA)),
    BPF_STMT (BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
  };
  struct sock_fprog program = {
    .len = (unsigned short) (sizeof (filter) / sizeof (filter[0])),
    .filter = filter,
  };

  if (prctl (PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) < 0)
    return -1;

  if (prctl (PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program) < 0)
    return -1;

  return 0;
}

int
main (int argc, char **argv)
{
  const char *real_crun = getenv ("REAL_CRUN");

  if (argc < 1 || real_crun == NULL || real_crun[0] == '\0')
    {
      fprintf (stderr, "REAL_CRUN must name the executable to run\n");
      return 2;
    }

  if (install_filter () < 0)
    {
      perror ("install seccomp filter");
      return 2;
    }

  argv[0] = (char *) real_crun;
  execv (real_crun, argv);

  perror ("execv");
  return 127;
}
