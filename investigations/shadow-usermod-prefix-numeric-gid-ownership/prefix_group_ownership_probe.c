#define _GNU_SOURCE
#include <errno.h>
#include <grp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static const char *group_file;

static struct group *dup_group(const struct group *src)
{
    if (!src)
        return NULL;

    struct group *g = calloc(1, sizeof(*g));
    if (!g)
        return NULL;

    g->gr_gid = src->gr_gid;
    g->gr_name = strdup(src->gr_name);
    g->gr_passwd = strdup(src->gr_passwd ? src->gr_passwd : "");

    size_t n = 0;
    while (src->gr_mem && src->gr_mem[n])
        n++;

    g->gr_mem = calloc(n + 1, sizeof(char *));
    if (!g->gr_name || !g->gr_passwd || !g->gr_mem)
        abort();

    for (size_t i = 0; i < n; i++) {
        g->gr_mem[i] = strdup(src->gr_mem[i]);
        if (!g->gr_mem[i])
            abort();
    }
    return g;
}

static void shadow_gr_free(struct group *g)
{
    free(g->gr_name);
    free(g->gr_passwd);
    if (g->gr_mem) {
        for (size_t i = 0; g->gr_mem[i]; i++)
            free(g->gr_mem[i]);
        free(g->gr_mem);
    }
    free(g);
}

static struct group *prefix_getgrnam_model(const char *name)
{
    FILE *f = fopen(group_file, "r");
    if (!f)
        return NULL;

    struct group *g = NULL;
    while ((g = fgetgrent(f)) != NULL)
        if (strcmp(name, g->gr_name) == 0)
            break;

    fclose(f);
    return g;
}

static struct group *prefix_getgrgid_model(gid_t gid)
{
    FILE *f = fopen(group_file, "r");
    if (!f)
        return NULL;

    struct group *g = NULL;
    while ((g = fgetgrent(f)) != NULL)
        if (gid == g->gr_gid)
            break;

    fclose(f);
    return g;
}

/* Mirrors the ownership split in current shadow prefix_getgr_nam_gid(). */
static struct group *prefix_getgr_nam_gid_model(const char *s)
{
    char *end = NULL;
    errno = 0;
    unsigned long v = strtoul(s, &end, 10);

    if (!errno && end && *s && *end == '\0')
        return prefix_getgrgid_model((gid_t)v); /* numeric: borrowed */

    struct group *g = prefix_getgrnam_model(s);
    return g ? dup_group(g) : NULL;             /* name: owned */
}

static int run_case(const char *arg)
{
    struct group *g = prefix_getgr_nam_gid_model(arg);
    if (!g)
        return 3;

    printf("arg=%s resolved=%s gid=%u ptr=%p\n",
           arg, g->gr_name, (unsigned)g->gr_gid, (void *)g);
    shadow_gr_free(g);
    return 0;
}

int main(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);

    char path[] = "/tmp/shadow-group-XXXXXX";
    int fd = mkstemp(path);
    if (fd < 0) {
        perror("mkstemp");
        return 2;
    }

    FILE *f = fdopen(fd, "w");
    if (!f) {
        perror("fdopen");
        return 2;
    }
    fputs("users:x:4242:alice\n", f);
    fclose(f);
    group_file = path;

    const char *cases[] = { "users", "4242" };
    for (size_t i = 0; i < 2; i++) {
        pid_t p = fork();
        if (p < 0) {
            perror("fork");
            return 2;
        }
        if (p == 0)
            _exit(run_case(cases[i]));

        int st = 0;
        if (waitpid(p, &st, 0) < 0) {
            perror("waitpid");
            return 2;
        }

        if (WIFSIGNALED(st))
            printf("result arg=%s signal=%d\n", cases[i], WTERMSIG(st));
        else
            printf("result arg=%s exit=%d\n", cases[i], WEXITSTATUS(st));
    }

    unlink(path);
    return 0;
}
