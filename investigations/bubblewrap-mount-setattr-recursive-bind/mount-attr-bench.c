/* Synthetic Linux Fieldwork microbenchmark.
 * Measures only attribute-application time on an already-created bind tree.
 * This is evidence machinery, not an upstream Bubblewrap candidate.
 */
#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/mount.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

#ifndef AT_RECURSIVE
#define AT_RECURSIVE 0x8000
#endif
#ifndef AT_EMPTY_PATH
#define AT_EMPTY_PATH 0x1000
#endif
#ifndef MOUNT_ATTR_NOSUID
#define MOUNT_ATTR_NOSUID 0x00000002
#endif
#ifndef MOUNT_ATTR_NODEV
#define MOUNT_ATTR_NODEV 0x00000004
#endif

static long long
elapsed_ns (struct timespec before, struct timespec after)
{
  return (after.tv_sec - before.tv_sec) * 1000000000LL
         + (after.tv_nsec - before.tv_nsec);
}

int
main (int argc, char **argv)
{
  const char *mode;
  const char *base;
  struct timespec before;
  struct timespec after;
  int n;

  if (argc != 4)
    return 64;

  mode = argv[1];
  base = argv[2];
  n = atoi (argv[3]);

  if (clock_gettime (CLOCK_MONOTONIC_RAW, &before) != 0)
    return 1;

  if (strcmp (mode, "mount-setattr") == 0)
    {
#ifdef __NR_mount_setattr
      struct mount_attr attr = { 0 };
      int fd = open (base, O_PATH | O_CLOEXEC);

      if (fd < 0)
        {
          perror ("open");
          return 1;
        }

      attr.attr_set = MOUNT_ATTR_NOSUID | MOUNT_ATTR_NODEV;
      if (syscall (__NR_mount_setattr,
                   fd,
                   "",
                   AT_EMPTY_PATH | AT_RECURSIVE,
                   &attr,
                   sizeof (attr)) != 0)
        {
          perror ("mount_setattr");
          return 1;
        }

      close (fd);
#else
      errno = ENOSYS;
      perror ("mount_setattr");
      return 1;
#endif
    }
  else if (strcmp (mode, "legacy") == 0)
    {
      unsigned long flags = MS_SILENT | MS_BIND | MS_REMOUNT
                            | MS_NOSUID | MS_NODEV | MS_RELATIME;
      int i;

      if (mount ("none", base, NULL, flags, NULL) != 0)
        {
          perror ("mount root");
          return 1;
        }

      for (i = 0; i < n; i++)
        {
          char path[4096];

          if (snprintf (path, sizeof (path), "%s/m%05d", base, i)
              >= (int) sizeof (path))
            return 1;

          if (mount ("none", path, NULL, flags, NULL) != 0)
            {
              perror ("mount child");
              return 1;
            }
        }
    }
  else
    return 64;

  if (clock_gettime (CLOCK_MONOTONIC_RAW, &after) != 0)
    return 1;

  printf ("%lld\n", elapsed_ns (before, after));
  return 0;
}
