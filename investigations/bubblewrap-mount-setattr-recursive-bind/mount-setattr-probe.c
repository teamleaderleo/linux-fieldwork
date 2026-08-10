/* Synthetic Linux Fieldwork probe for recursive mount attributes.
 * This is evidence machinery, not an upstream Bubblewrap candidate.
 */
#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/mount.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>

#ifndef AT_RECURSIVE
#define AT_RECURSIVE 0x8000
#endif
#ifndef AT_EMPTY_PATH
#define AT_EMPTY_PATH 0x1000
#endif
#ifndef MOUNT_ATTR_RDONLY
#define MOUNT_ATTR_RDONLY 0x00000001
#endif
#ifndef MOUNT_ATTR_NOSUID
#define MOUNT_ATTR_NOSUID 0x00000002
#endif
#ifndef MOUNT_ATTR_NODEV
#define MOUNT_ATTR_NODEV 0x00000004
#endif

static int
apply_recursive_attributes (int fd, unsigned long long attr_set)
{
#ifdef __NR_mount_setattr
  struct mount_attr attr = { 0 };

  attr.attr_set = attr_set;
  return (int) syscall (__NR_mount_setattr,
                        fd,
                        "",
                        AT_EMPTY_PATH | AT_RECURSIVE,
                        &attr,
                        sizeof (attr));
#else
  (void) fd;
  (void) attr_set;
  errno = ENOSYS;
  return -1;
#endif
}

int
main (int argc, char **argv)
{
  unsigned long long attr_set = MOUNT_ATTR_NOSUID;
  int fd;
  int saved_errno;

  if (argc != 3)
    {
      fprintf (stderr, "usage: %s PATH bind|dev-bind|ro-bind\n", argv[0]);
      return 64;
    }

  if (strcmp (argv[2], "bind") == 0)
    attr_set |= MOUNT_ATTR_NODEV;
  else if (strcmp (argv[2], "dev-bind") == 0)
    {
      /* Preserve the source mount's existing device policy. */
    }
  else if (strcmp (argv[2], "ro-bind") == 0)
    attr_set |= MOUNT_ATTR_NODEV | MOUNT_ATTR_RDONLY;
  else
    {
      fprintf (stderr, "unknown mode: %s\n", argv[2]);
      return 64;
    }

  fd = open (argv[1], O_PATH | O_CLOEXEC);
  if (fd < 0)
    {
      perror ("open(O_PATH)");
      return errno ? errno : 1;
    }

  if (apply_recursive_attributes (fd, attr_set) == 0)
    {
      close (fd);
      puts ("ok");
      return 0;
    }

  saved_errno = errno;
  close (fd);
  fprintf (stderr,
           "mount_setattr: errno=%d (%s)\n",
           saved_errno,
           strerror (saved_errno));
  return saved_errno ? saved_errno : 1;
}
