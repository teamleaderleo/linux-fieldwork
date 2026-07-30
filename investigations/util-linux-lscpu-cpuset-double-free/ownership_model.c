#include <stdio.h>
#include <stdlib.h>

/*
 * This is a deterministic ownership model, not a copy of util-linux.
 * It preserves the relevant sequence:
 *
 *   parser publishes an allocated pointer
 *   parser detects invalid input and frees it
 *   outer lscpu cleanup later frees the published pointer
 *
 * The tracker reports the second logical free without invoking undefined
 * behavior in the regression itself.
 */

static int allocation_token;
static void *first_freed;
static int duplicate_free;

static void tracked_free(void *pointer)
{
	if (pointer == NULL)
		return;
	if (pointer == first_freed) {
		duplicate_free = 1;
		return;
	}
	first_freed = pointer;
}

static int parse_cpuset(void **output)
{
	int rc = -1;

	*output = &allocation_token;

	if (rc) {
		tracked_free(*output);
#ifdef CLEAR_OUTPUT_AFTER_ERROR
		*output = NULL;
#endif
	}
	return rc;
}

int main(void)
{
	void *node_map = NULL;

	if (parse_cpuset(&node_map) == 0)
		return 2;

	tracked_free(node_map);

	if (duplicate_free) {
		fputs("duplicate cleanup detected\n", stderr);
		return 42;
	}

	puts("cleanup is idempotent after parse failure");
	return 0;
}
