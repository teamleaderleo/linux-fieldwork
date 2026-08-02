#define _GNU_SOURCE
#include <fnmatch.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static double
monotonic_seconds(void)
{
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
        perror("clock_gettime");
        exit(3);
    }
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1000000000.0;
}

int
main(int argc, char **argv)
{
    const char *pattern;
    char *string;
    char *end;
    long length;
    long repetitions;
    int final_character;
    int flags;
    volatile int result = 0;
    double begin;
    double elapsed;

    if (argc != 6) {
        fprintf(stderr,
                "usage: %s PATTERN A_COUNT FINAL_CHARACTER FLAGS REPETITIONS\n",
                argv[0]);
        return 2;
    }
    if (setlocale(LC_ALL, "") == NULL) {
        perror("setlocale");
        return 4;
    }

    pattern = argv[1];
    length = strtol(argv[2], &end, 10);
    if (*end != '\0' || length < 0)
        return 2;
    if (argv[3][0] == '\0' || argv[3][1] != '\0')
        return 2;
    final_character = (unsigned char)argv[3][0];
    flags = (int)strtol(argv[4], &end, 0);
    if (*end != '\0')
        return 2;
    repetitions = strtol(argv[5], &end, 10);
    if (*end != '\0' || repetitions < 1)
        return 2;

    string = malloc((size_t)length + 2);
    if (string == NULL) {
        perror("malloc");
        return 3;
    }
    memset(string, 'a', (size_t)length);
    string[length] = (char)final_character;
    string[length + 1] = '\0';

    begin = monotonic_seconds();
    for (long i = 0; i < repetitions; ++i)
        result |= fnmatch(pattern, string, flags);
    elapsed = monotonic_seconds() - begin;

    printf("%s,%ld,%c,%d,%ld,%d,%.9f,%.9f\n",
           pattern,
           length,
           final_character,
           flags,
           repetitions,
           result,
           elapsed,
           elapsed / repetitions);

    free(string);
    return 0;
}
