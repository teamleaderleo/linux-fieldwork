#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int
parse_integer (int *value, const char *text)
{
  char *end = NULL;
  long parsed;

  errno = 0;
  parsed = strtol (text, &end, 0);
  if (text == NULL || text[0] == '\0' || end == text || *end != '\0')
    return -1;
  if ((parsed == LONG_MAX || parsed == LONG_MIN) && errno == ERANGE)
    return -1;
  if (parsed < INT_MIN || parsed > INT_MAX)
    return -1;

  *value = (int) parsed;
  return 0;
}

static int
open_old_style (const char *text)
{
  char path[128];
  int pid;
  int fd;

  if (parse_integer (&pid, text) < 0)
    return -1;

  snprintf (path, sizeof (path), "/proc/%d/ns/net", pid);
  fd = open (path, O_RDONLY);
  printf ("old %-12s -> %-24s : %s\n",
          text, path, fd >= 0 ? "OK" : strerror (errno));
  return fd;
}

static int
open_current_style (const char *text)
{
  char path[128];
  int pid;
  int fd;

  if (parse_integer (&pid, text) < 0)
    return -1;

  snprintf (path, sizeof (path), "/proc/%s/ns/net", text);
  fd = open (path, O_RDONLY);
  printf ("new %-12s -> %-24s : %s\n",
          text, path, fd >= 0 ? "OK" : strerror (errno));
  return fd;
}

int
main (void)
{
  char decimal[32];
  char hexadecimal[32];
  char octal[32];
  const char *forms[3];
  int pid = getpid ();
  size_t i;

  snprintf (decimal, sizeof (decimal), "%d", pid);
  snprintf (hexadecimal, sizeof (hexadecimal), "0x%x", pid);
  snprintf (octal, sizeof (octal), "0%o", pid);

  forms[0] = decimal;
  forms[1] = hexadecimal;
  forms[2] = octal;

  printf ("pid=%d\n", pid);
  for (i = 0; i < 3; i++)
    {
      int fd = open_old_style (forms[i]);
      if (fd >= 0)
        close (fd);

      fd = open_current_style (forms[i]);
      if (fd >= 0)
        close (fd);
    }

  return 0;
}
